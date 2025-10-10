"""生成任务模块，串联文本生图、图生视频、后期处理与上传。"""

from __future__ import annotations

import hashlib
import re
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

from ..config import PipelineConfig, load_config
from ..prompts.pool import PromptCandidate, PromptPool, load_prompt_pool
from ..sd.img2vid import Img2VidGenerator
from ..sd.txt2img import Txt2ImgGenerator
from ..uploader.interfaces import DraftResult, UploadMetadata
from ..uploader.router import upload_video
from ..video.postprocess import auto_postprocess

console = Console()


def _slugify(text: str) -> str:
    """将标题转换为文件名安全的 slug。"""

    normalized = re.sub(r"[^0-9A-Za-z一-龥]+", "-", text)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized[:24] or "video"


@dataclass
class JobResult:
    """封装单次流水线的产出信息。"""

    prompt: PromptCandidate
    image_path: Path
    raw_video_path: Path
    final_video_path: Path
    cover_path: Optional[Path]
    file_hash: str
    duration: float
    upload_result: DraftResult
    metadata: dict
    success: bool
    error: Optional[str] = None


class GenerationJob:
    """负责执行从采样到视频导出的完整流程。"""

    def __init__(self, config: PipelineConfig, prompt_pool: PromptPool) -> None:
        self.config = config
        self.prompt_pool = prompt_pool
        self.txt2img = Txt2ImgGenerator(config)
        self.img2vid = Img2VidGenerator(config)

    @classmethod
    def from_config(cls, config_path: Optional[Path] = None) -> "GenerationJob":
        """加载配置并初始化依赖。"""

        config = load_config(config_path)
        pool = load_prompt_pool(config.prompt_pool_path) if config.prompt_pool_path else load_prompt_pool()
        pool.extend_texts(config.prompts.extra_texts)
        pool.extend_styles(config.prompts.extra_styles)
        pool.extend_tags(config.prompts.extra_tags)
        pool.add_blacklist(config.prompts.blacklist_topics)
        pool.add_sensitive_words(config.prompts.sensitive_words)
        return cls(config=config, prompt_pool=pool)

    def run(self) -> JobResult:
        """执行一次完整的生成任务。"""

        start_time = time.perf_counter()
        candidate = self.prompt_pool.sample(
            max_title=self.config.prompts.max_title_length,
            max_desc=self.config.prompts.max_desc_length,
            max_tags=self.config.prompts.max_tags,
            sampling_cfg=self.config.raw_data.get("sampling", {}),
        )
        console.log(f"[bold cyan]选定 Prompt：[/bold cyan]{candidate.prompt}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = _slugify(candidate.title)
        output_tmp_dir = self.config.storage.tmp_dir / f"{timestamp}_{slug}"
        output_tmp_dir.mkdir(parents=True, exist_ok=True)

        image_path = output_tmp_dir / "txt2img.json"
        txt2img_result = self.txt2img.generate(
            prompt=candidate.prompt,
            negative_prompt=self.config.raw_data.get("sd", {}).get("negative_prompt", ""),
            output_path=image_path,
            seed=candidate.seed,
        )

        video_path = output_tmp_dir / "img2vid.mp4"
        img2vid_result = self.img2vid.generate(image_path=txt2img_result.image_path, output_path=video_path, seed=candidate.seed)

        processed_path = auto_postprocess(
            config=self.config,
            video_path=img2vid_result.video_path,
            title=candidate.title,
            enable_subtitle=self.config.raw_data.get("postprocess", {}).get("subtitle", False),
            enable_watermark=self.config.raw_data.get("postprocess", {}).get("watermark", False),
        )

        final_name = f"{timestamp}_{slug}.mp4"
        final_path = self.config.storage.output_dir / final_name
        shutil.move(processed_path, final_path)

        cover_path = None
        if self.config.video.cover_export:
            potential_cover = self.config.storage.cover_dir / f"{final_path.stem}.jpg"
            if potential_cover.exists():
                cover_path = potential_cover

        file_hash = ""
        if final_path.exists():
            sha = hashlib.sha256()
            with final_path.open("rb") as fp:
                for chunk in iter(lambda: fp.read(1024 * 1024), b""):
                    sha.update(chunk)
            file_hash = sha.hexdigest()

        metadata = {
            "prompt": candidate.prompt,
            "title": candidate.title,
            "description": candidate.description,
            "tags": candidate.tags,
            "seed": candidate.seed,
            "sd_backend": self.config.sd.backend,
            "video_backend": self.config.animate.backend,
        }

        upload_metadata = UploadMetadata(
            title=candidate.title,
            description=candidate.description,
            tags=candidate.tags,
            extra={"seed": str(candidate.seed), "hash": file_hash},
        )
        upload_result = upload_video(self.config, final_path, upload_metadata)

        duration = time.perf_counter() - start_time
        console.log(f"[green]任务完成，用时 {duration:.2f}s，输出文件 {final_path}[/green]")

        return JobResult(
            prompt=candidate,
            image_path=txt2img_result.image_path,
            raw_video_path=img2vid_result.video_path,
            final_video_path=final_path,
            cover_path=cover_path,
            file_hash=file_hash,
            duration=duration,
            upload_result=upload_result,
            metadata=metadata,
            success=True,
        )


__all__ = ["GenerationJob", "JobResult"]
