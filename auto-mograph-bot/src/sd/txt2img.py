"""Text to image generation stub implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from rich.console import Console

console = Console()


class Txt2ImgGenerator:
    """Interface for Stable Diffusion text-to-image generation."""

    def __init__(self, model_path: Optional[Path] = None, sampler: str = "ddim") -> None:
        self.model_path = model_path
        self.sampler = sampler

    def generate(self, prompt: str, output_path: Path, options: Optional[Dict[str, float]] = None) -> Path:
        """Generate an image for the given prompt.

        This stub simulates generation by writing prompt metadata to a text file.
        Replace with diffusers or WebUI API calls as needed.
        """

        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = [
            f"Prompt: {prompt}",
            f"Sampler: {self.sampler}",
            f"Model path: {self.model_path}",
            f"Options: {options or {}}",
        ]
        output_path.write_text("\n".join(content), encoding="utf-8")
        console.log(f"[green]Generated[/green] placeholder image at {output_path}")
        return output_path


__all__ = ["Txt2ImgGenerator"]
