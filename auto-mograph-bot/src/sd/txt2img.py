"""Stable Diffusion 文本生图封装，支持 diffusers 或 SD WebUI 两种后端。"""

from __future__ import annotations

import functools
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import httpx
from rich.console import Console

from ..config import PipelineConfig
from ..logging.structlog import log_event, log_exception

console = Console()

_RETRY_CFG: Dict[str, Any] = {"max_attempts": 1, "backoff_factor": 1.0, "jitter_ms": 0}


def configure_sd_retry(settings: Any) -> None:
    """更新默认的 SD 调用重试配置。"""

    global _RETRY_CFG
    if settings is None:
        return
    data: Dict[str, Any]
    if hasattr(settings, "model_dump"):
        data = settings.model_dump()
    elif isinstance(settings, dict):
        data = settings
    else:
        data = dict(settings)
    updated = {
        "max_attempts": int(data.get("max_attempts", _RETRY_CFG["max_attempts"])),
        "backoff_factor": float(data.get("backoff_factor", _RETRY_CFG["backoff_factor"])),
        "jitter_ms": int(data.get("jitter_ms", _RETRY_CFG["jitter_ms"])),
    }
    _RETRY_CFG = updated
    log_event("retry_config_updated", component="sd", config=updated)


def get_retry_cfg() -> Dict[str, Any]:
    """返回当前的重试配置副本。"""

    return dict(_RETRY_CFG)


def _normalize_retry_cfg(raw: Optional[Any]) -> Dict[str, Any]:
    if raw is None:
        return get_retry_cfg()
    if hasattr(raw, "model_dump"):
        raw = raw.model_dump()
    if isinstance(raw, dict):
        cfg = raw
    else:
        cfg = dict(raw)
    return {
        "max_attempts": max(1, int(cfg.get("max_attempts", _RETRY_CFG["max_attempts"]))),
        "backoff_factor": max(1.0, float(cfg.get("backoff_factor", _RETRY_CFG["backoff_factor"]))),
        "jitter_ms": max(0, int(cfg.get("jitter_ms", _RETRY_CFG["jitter_ms"]))),
    }


def classify_sd_error(err: Exception) -> Tuple[str, str]:
    """根据异常内容给出错误类别与修复建议。"""

    message = str(err).lower()
    if isinstance(err, httpx.TimeoutException) or "timeout" in message:
        return "timeout", "检查网络连通性或适当提高超时时间"
    if isinstance(err, httpx.ConnectError) or "connection refused" in message:
        return "conn_error", "确认 SD WebUI 服务已启动且地址配置正确"
    if isinstance(err, httpx.HTTPStatusError):
        status = err.response.status_code
        if status == 429:
            return "rate_limited", "降低并发或延长请求间隔"
        if 500 <= status < 600:
            return "http_5xx", "检查 WebUI 服务端日志或重启服务"
        if 400 <= status < 500:
            return "bad_request", "校验提示词与参数是否符合接口要求"
    if isinstance(err, httpx.RequestError):
        return "conn_error", "检查网络代理、防火墙或服务监听端口"
    if "out of memory" in message or "cuda" in message and "memory" in message:
        return "oom", "降低生成分辨率或减少批量大小"
    if "unauthorized" in message or "401" in message:
        return "auth_error", "确认 WebUI Token 或鉴权配置是否有效"
    return "unknown", "查看 pipeline.jsonl 中的 traceback 以进一步排查"


def with_retry(fn):  # type: ignore[no-untyped-def]
    """为 SD 调用增加指数退避与结构化日志。"""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
        cfg = _normalize_retry_cfg(kwargs.pop("_retry_cfg", None))
        log_ctx = kwargs.pop("_log_ctx", {})
        attempts = max(1, int(cfg.get("max_attempts", 1)))
        backoff = max(1.0, float(cfg.get("backoff_factor", 1.0)))
        jitter_ms = max(0, int(cfg.get("jitter_ms", 0)))
        delay = 1.0
        for attempt in range(1, attempts + 1):
            log_event(
                "sd_call_start",
                fn=fn.__name__,
                attempt=attempt,
                max_attempts=attempts,
                **log_ctx,
            )
            start = time.time()
            try:
                result = fn(*args, **kwargs)
                elapsed_ms = int((time.time() - start) * 1000)
                log_event(
                    "sd_call_success",
                    fn=fn.__name__,
                    attempt=attempt,
                    elapsed_ms=elapsed_ms,
                    **log_ctx,
                )
                return result
            except Exception as err:  # noqa: BLE001
                elapsed_ms = int((time.time() - start) * 1000)
                category, hint = classify_sd_error(err)
                log_exception(
                    "sd_call_fail",
                    err,
                    fn=fn.__name__,
                    attempt=attempt,
                    elapsed_ms=elapsed_ms,
                    category=category,
                    hint=hint,
                    **log_ctx,
                )
                if attempt >= attempts:
                    raise
                jitter = random.randint(0, jitter_ms) / 1000.0 if jitter_ms else 0.0
                sleep_seconds = delay + jitter
                log_event(
                    "sd_call_retry",
                    fn=fn.__name__,
                    attempt=attempt,
                    next_delay_ms=int(sleep_seconds * 1000),
                    category=category,
                    hint=hint,
                    **log_ctx,
                )
                time.sleep(sleep_seconds)
                delay *= backoff
        raise RuntimeError("SD call exhausted all retry attempts")

    return wrapper


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

    def __init__(self, model_path: Optional[Path], retry_cfg: Optional[Dict[str, Any]] = None) -> None:
        self.model_path = model_path
        self.retry_cfg = _normalize_retry_cfg(retry_cfg)

    @with_retry
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
        log_event(
            "sd_diffusers_placeholder",
            backend="diffusers",
            output=str(output_path),
            seed=seed,
        )
        return Txt2ImgResult(image_path=output_path, seed=seed)


class WebUITxt2ImgBackend(BaseTxt2ImgBackend):
    """对接 Stable Diffusion WebUI 的 HTTP API。"""

    def __init__(self, base_url: str, token: Optional[str] = None, retry_cfg: Optional[Dict[str, Any]] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.retry_cfg = _normalize_retry_cfg(retry_cfg)

    @with_retry
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
        log_event(
            "sd_webui_response_saved",
            backend="webui",
            output=str(output_path),
            seed=seed,
        )
        return Txt2ImgResult(image_path=output_path, seed=seed)


class Txt2ImgGenerator:
    """文案生图统一入口，根据配置选择具体后端。"""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        sd_config = config.sd
        if sd_config.backend == "webui" and not sd_config.webui_url:
            raise ValueError("配置为 WebUI 后端时必须提供 SD_WEBUI_URL 或 sd.webui_url")
        self.backend: BaseTxt2ImgBackend
        retry_cfg = get_retry_cfg()
        if sd_config.backend == "webui":
            self.backend = WebUITxt2ImgBackend(
                sd_config.webui_url or "http://127.0.0.1:7860",
                sd_config.webui_token,
                retry_cfg,
            )
        else:
            self.backend = DiffusersTxt2ImgBackend(sd_config.model_path, retry_cfg)
        self.retry_cfg = retry_cfg

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
            log_event(
                "sd_dry_run",
                backend=self.config.sd.backend,
                output=str(output_path),
                seed=final_seed,
            )
            return Txt2ImgResult(image_path=output_path, seed=final_seed)

        return self.backend.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            output_path=output_path,
            seed=final_seed,
            _retry_cfg=self.retry_cfg,
            _log_ctx={
                "backend": self.config.sd.backend,
                "seed": final_seed,
            },
        )


__all__ = ["Txt2ImgGenerator", "Txt2ImgResult", "configure_sd_retry", "with_retry", "get_retry_cfg"]
