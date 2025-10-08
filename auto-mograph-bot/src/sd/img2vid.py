"""Image to video generation stub implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


class Img2VidGenerator:
    """AnimateDiff / Stable Video Diffusion wrapper stub."""

    def __init__(self, model_path: Optional[Path] = None, motion_module: Optional[Path] = None) -> None:
        self.model_path = model_path
        self.motion_module = motion_module

    def generate(self, image_path: Path, output_path: Path, num_frames: int = 24, fps: int = 30) -> Path:
        """Simulate turning an image into a short video clip."""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        metadata = [
            f"Source image: {image_path}",
            f"Frames: {num_frames}",
            f"FPS: {fps}",
            f"Model path: {self.model_path}",
            f"Motion module: {self.motion_module}",
        ]
        output_path.write_text("\n".join(metadata), encoding="utf-8")
        console.log(f"[blue]Generated[/blue] placeholder video at {output_path}")
        return output_path


__all__ = ["Img2VidGenerator"]
