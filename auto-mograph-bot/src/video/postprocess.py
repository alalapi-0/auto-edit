"""Simple post-processing helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


def adapt_vertical(input_path: Path, output_path: Path, resolution: tuple[int, int] = (1080, 1920)) -> Path:
    """Placeholder vertical adaptation."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        f"Adapted {input_path} to vertical resolution {resolution[0]}x{resolution[1]}",
        encoding="utf-8",
    )
    console.log(f"Adapted video saved to {output_path}")
    return output_path


def add_subtitles(video_path: Path, subtitle_path: Path, output_path: Optional[Path] = None) -> Path:
    if output_path is None:
        output_path = video_path.with_name(f"{video_path.stem}_subtitled{video_path.suffix}")
    output_path.write_text(f"Subtitles from {subtitle_path} applied to {video_path}", encoding="utf-8")
    console.log(f"Subtitled video saved to {output_path}")
    return output_path


def apply_watermark(video_path: Path, watermark_path: Path, output_path: Optional[Path] = None) -> Path:
    if output_path is None:
        output_path = video_path.with_name(f"{video_path.stem}_watermarked{video_path.suffix}")
    output_path.write_text(f"Watermark {watermark_path} applied to {video_path}", encoding="utf-8")
    console.log(f"Watermarked video saved to {output_path}")
    return output_path


__all__ = ["adapt_vertical", "add_subtitles", "apply_watermark"]
