"""图生视频模块，封装 AnimateDiff 与 Stable Video Diffusion 占位实现。"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from rich.console import Console

from ..config import PipelineConfig
from ..logging.structlog import log_event
from ..video.ffmpeg_utils import create_placeholder_clip
from .txt2img import get_retry_cfg, with_retry

console = Console()


@dataclass
class Img2VidResult:
    """图生视频的输出结构。"""

    video_path: Path
    seed: int


class BaseImg2VidBackend:
    """后端基类，便于扩展。"""

    def generate(
        self,
        image_path: Path,
        output_path: Path,
        seed: int,
        fps: int,
        num_frames: int,
        width: int,
        height: int,
    ) -> Img2VidResult:
        raise NotImplementedError


class AnimateDiffBackend(BaseImg2VidBackend):
    """AnimateDiff 占位实现。"""

    def __init__(
        self,
        model_path: Optional[Path],
        motion_module: Optional[Path],
    ) -> None:
        self.model_path = model_path
        self.motion_module = motion_module

    @with_retry
    def generate(
        self,
        image_path: Path,
        output_path: Path,
        seed: int,
        fps: int,
        num_frames: int,
        width: int,
        height: int,
    ) -> Img2VidResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        metadata = {
            "backend": "animatediff",
            "image": str(image_path),
            "model_path": str(self.model_path) if self.model_path else None,
            "motion_module": str(self.motion_module) if self.motion_module else None,
            "seed": seed,
            "fps": fps,
            "num_frames": num_frames,
        }
        meta_path = output_path.with_suffix(".json")
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        duration = max(1, num_frames // max(1, fps))
        create_placeholder_clip(output_path, width=width, height=height, duration=duration, fps=fps, text="AnimateDiff 占位")
        console.log(f"[blue]AnimateDiff 占位视频已生成：[/blue]{output_path}")
        log_event(
            "img2vid_placeholder",
            backend="animatediff",
            output=str(output_path),
            seed=seed,
            fps=fps,
            frames=num_frames,
        )
        return Img2VidResult(video_path=output_path, seed=seed)


class StableVideoDiffusionBackend(BaseImg2VidBackend):
    """Stable Video Diffusion 占位实现。"""

    def __init__(self, model_path: Optional[Path]) -> None:
        self.model_path = model_path

    @with_retry
    def generate(
        self,
        image_path: Path,
        output_path: Path,
        seed: int,
        fps: int,
        num_frames: int,
        width: int,
        height: int,
    ) -> Img2VidResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        metadata = {
            "backend": "svd",
            "image": str(image_path),
            "model_path": str(self.model_path) if self.model_path else None,
            "seed": seed,
            "fps": fps,
            "num_frames": num_frames,
        }
        meta_path = output_path.with_suffix(".json")
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        duration = max(1, num_frames // max(1, fps))
        create_placeholder_clip(output_path, width=width, height=height, duration=duration, fps=fps, text="SVD 占位")
        console.log(f"[blue]SVD 占位视频已生成：[/blue]{output_path}")
        log_event(
            "img2vid_placeholder",
            backend="svd",
            output=str(output_path),
            seed=seed,
            fps=fps,
            frames=num_frames,
        )
        return Img2VidResult(video_path=output_path, seed=seed)


class Img2VidGenerator:
    """统一的图生视频生成器，根据配置选择后端。"""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        animate_cfg = config.animate
        if animate_cfg.backend == "svd":
            self.backend = StableVideoDiffusionBackend(animate_cfg.model_path)
        else:
            self.backend = AnimateDiffBackend(
                animate_cfg.model_path,
                animate_cfg.motion_module,
            )
        self.retry_cfg: Dict[str, object] = get_retry_cfg()

    def generate(self, image_path: Path, output_path: Path, seed: Optional[int] = None) -> Img2VidResult:
        """执行图生视频流程。"""

        final_seed = seed if seed is not None else random.randint(0, 2**32 - 1)
        animate_cfg = self.config.animate
        if self.config.runtime.dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps({
                    "backend": animate_cfg.backend,
                    "image": str(image_path),
                    "seed": final_seed,
                    "dry_run": True,
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            console.log(f"[yellow]Dry-run 模式下未真正推理视频：[/yellow]{output_path}")
            log_event(
                "img2vid_dry_run",
                backend=animate_cfg.backend,
                output=str(output_path),
                seed=final_seed,
            )
            return Img2VidResult(video_path=output_path, seed=final_seed)

        return self.backend.generate(
            image_path=image_path,
            output_path=output_path,
            seed=final_seed,
            fps=animate_cfg.fps,
            num_frames=animate_cfg.num_frames,
            width=self.config.video.width,
            height=self.config.video.height,
            _retry_cfg=self.retry_cfg,
            _log_ctx={
                "backend": animate_cfg.backend,
                "seed": final_seed,
            },
        )


__all__ = ["Img2VidGenerator", "Img2VidResult"]
