"""High level orchestration for generation jobs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.console import Console

from ..config import PipelineConfig, load_config
from ..prompts import PromptPool
from ..sd import Img2VidGenerator, Txt2ImgGenerator
from ..video import adapt_vertical

console = Console()


@dataclass
class GenerationJob:
    """Represents a single text-to-video pipeline run."""

    config: PipelineConfig
    prompt_pool: PromptPool
    txt2img: Txt2ImgGenerator
    img2vid: Img2VidGenerator

    @classmethod
    def from_config(cls, config_path: Optional[Path] = None) -> "GenerationJob":
        config = load_config(config_path)
        prompt_pool = PromptPool()
        if config.prompt_pool_path and config.prompt_pool_path.exists():
            prompt_pool.extend_texts(config.prompt_pool_path.read_text(encoding="utf-8").splitlines())
        else:
            prompt_pool.extend_texts(["A cyberpunk cityscape at dusk"])

        txt2img = Txt2ImgGenerator(model_path=config.model_paths.txt2img)
        img2vid = Img2VidGenerator(model_path=config.model_paths.img2vid)

        return cls(config=config, prompt_pool=prompt_pool, txt2img=txt2img, img2vid=img2vid)

    def run(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        prompt = self.prompt_pool.sample_combo()
        console.log(f"Using prompt: {prompt}")

        image_path = output_dir / "frame.txt"
        video_stub = output_dir / "animation.txt"
        final_video = output_dir / "final.txt"

        self.txt2img.generate(prompt, image_path)
        self.img2vid.generate(image_path, video_stub, fps=self.config.video.fps)
        adapt_vertical(video_stub, final_video, resolution=(self.config.video.width, self.config.video.height))

        console.log(f"Job completed, output at {final_video}")
        return final_video


__all__ = ["GenerationJob"]
