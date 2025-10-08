"""Stable Diffusion 文本生图封装，支持 diffusers 或 SD WebUI 两种后端。"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import httpx
from rich.console import Console

from ..config import PipelineConfig

console = Console()


@dataclass
class Txt2ImgResult:
    """封装文本生图结果。"""

    image_path: Path
    seed: int


class BaseTxt2ImgBackend:
    """后端基类，便于扩展不同实现。"""

    def generate(self, prompt: str, negative_prompt: str, output_path: Path, seed: int) -> Txt2ImgResult:
        raise NotImplementedError


class DiffusersTxt2ImgBackend(BaseTxt2ImgBackend):
    """使用 diffusers 本地推理的占位实现。"""

    def __init__(self, model_path: Optional[Path]) -> None:
        self.model_path = model_path

    def generate(self, prompt: str, negative_prompt: str, output_path: Path, seed: int) -> Txt2ImgResult:
        """占位逻辑：写入元数据，实际项目应替换为 diffusers 推理。"""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        metadata = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "model_path": str(self.model_path) if self.model_path else None,
            "seed": seed,
        }
        output_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        console.log(f"[green]Diffusers 后端写入占位图片：[/green]{output_path}")
        return Txt2ImgResult(image_path=output_path, seed=seed)


class WebUITxt2ImgBackend(BaseTxt2ImgBackend):
    """对接 Stable Diffusion WebUI 的 HTTP API。"""

    def __init__(self, base_url: str, token: Optional[str] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def generate(self, prompt: str, negative_prompt: str, output_path: Path, seed: int) -> Txt2ImgResult:
        payload: Dict[str, object] = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "seed": seed,
            "steps": 30,
        }
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        console.log(f"[cyan]请求 SD WebUI 接口：[/cyan]{self.base_url}/sdapi/v1/txt2img")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            response = httpx.post(f"{self.base_url}/sdapi/v1/txt2img", headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            console.log(f"[red]调用 WebUI 失败：{exc}[/red]")
            # 写入失败信息便于调试
            output_path.write_text(
                json.dumps({"error": str(exc), "prompt": prompt}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            raise

        data = response.json()
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        console.log(f"[green]已保存 WebUI 返回占位数据：[/green]{output_path}")
        return Txt2ImgResult(image_path=output_path, seed=seed)


class Txt2ImgGenerator:
    """文案生图统一入口，根据配置选择具体后端。"""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        sd_config = config.sd
        if sd_config.backend == "webui" and not sd_config.webui_url:
            raise ValueError("配置为 WebUI 后端时必须提供 SD_WEBUI_URL 或 sd.webui_url")
        self.backend: BaseTxt2ImgBackend
        if sd_config.backend == "webui":
            self.backend = WebUITxt2ImgBackend(sd_config.webui_url or "http://127.0.0.1:7860", sd_config.webui_token)
        else:
            self.backend = DiffusersTxt2ImgBackend(sd_config.model_path)

    def generate(self, prompt: str, negative_prompt: str, output_path: Path, seed: Optional[int] = None) -> Txt2ImgResult:
        """执行文本生图并返回结果。"""

        final_seed = seed if seed is not None else random.randint(0, 2**32 - 1)
        if self.config.runtime.dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps({
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "seed": final_seed,
                    "backend": self.config.sd.backend,
                    "dry_run": True,
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            console.log(f"[yellow]Dry-run 模式下仅写入文案信息：[/yellow]{output_path}")
            return Txt2ImgResult(image_path=output_path, seed=final_seed)

        return self.backend.generate(prompt=prompt, negative_prompt=negative_prompt, output_path=output_path, seed=final_seed)


__all__ = ["Txt2ImgGenerator", "Txt2ImgResult"]
