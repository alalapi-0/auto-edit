"""视频后期处理模块，包含竖屏适配、字幕、水印与音频混合等功能。"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Optional

from rich.console import Console

from ..config import PipelineConfig
from .ffmpeg_utils import ensure_ffmpeg_available, run_ffmpeg, extract_cover

console = Console()


def adapt_vertical(video_path: Path, output_path: Path, width: int, height: int) -> Path:
    """将输入视频裁剪/填充为指定竖屏分辨率。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ensure_ffmpeg_available(),
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"scale=w={width}:h={height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-preset",
        "medium",
        "-an",
        str(output_path),
    ]
    run_ffmpeg(command)
    return output_path


def add_subtitles(video_path: Path, subtitle_path: Path, output_path: Optional[Path] = None) -> Path:
    """为视频叠加外部字幕文件。"""

    if output_path is None:
        output_path = video_path.with_name(f"{video_path.stem}_subtitle{video_path.suffix}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ensure_ffmpeg_available(),
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"subtitles='{subtitle_path.as_posix()}'",
        "-c:a",
        "copy",
        str(output_path),
    ]
    run_ffmpeg(command)
    return output_path


def apply_watermark(video_path: Path, watermark_path: Path, output_path: Optional[Path] = None, position: str = "top_right") -> Path:
    """叠加角标水印，可配置位置。"""

    if output_path is None:
        output_path = video_path.with_name(f"{video_path.stem}_watermark{video_path.suffix}")
    mapping = {
        "top_left": "10:10",
        "top_right": "(main_w-overlay_w-10):10",
        "bottom_left": "10:(main_h-overlay_h-10)",
        "bottom_right": "(main_w-overlay_w-10):(main_h-overlay_h-10)",
    }
    offset = mapping.get(position, mapping["top_right"])
    command = [
        ensure_ffmpeg_available(),
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(watermark_path),
        "-filter_complex",
        f"[0:v][1:v]overlay={offset}",
        "-c:a",
        "copy",
        str(output_path),
    ]
    run_ffmpeg(command)
    return output_path


def mix_bgm(video_path: Path, bgm_path: Path, output_path: Path, volume: float = 0.6) -> Path:
    """将提示音/BGM 混合入主视频音轨。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ensure_ffmpeg_available(),
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(bgm_path),
        "-filter_complex",
        f"[1:a]volume={volume}[bgm]",
        "-map",
        "0:v",
        "-map",
        "[bgm]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(output_path),
    ]
    run_ffmpeg(command)
    return output_path


def auto_postprocess(
    config: PipelineConfig,
    video_path: Path,
    title: str,
    enable_subtitle: bool = False,
    enable_watermark: bool = False,
) -> Path:
    """执行竖屏适配及可选字幕/水印/BGM 的综合处理流程。"""

    tmp_vertical = config.storage.tmp_dir / f"{video_path.stem}_vertical.mp4"
    final_vertical = adapt_vertical(video_path, tmp_vertical, config.video.width, config.video.height)

    current_path = final_vertical
    subtitle_path: Optional[Path] = None
    watermark_path: Optional[Path] = None

    if enable_subtitle:
        subtitle_path = config.storage.tmp_dir / f"{video_path.stem}.srt"
        subtitle_path.write_text(
            "1\n00:00:00,000 --> 00:00:05,000\n" + title + "\n",
            encoding="utf-8",
        )
        current_path = add_subtitles(current_path, subtitle_path)

    if enable_watermark:
        watermark_path = config.storage.tmp_dir / "watermark.png"
        if not watermark_path.exists():
            console.log("[yellow]未找到水印图像，跳过水印步骤。[/yellow]")
        else:
            current_path = apply_watermark(current_path, watermark_path)

    if config.audio.enable_bgm:
        bgm_dir = config.audio.bgm_directory
        candidates = list(bgm_dir.glob("*.mp3")) + list(bgm_dir.glob("*.wav"))
        if candidates:
            bgm_path = random.choice(candidates)
            current_path = mix_bgm(current_path, bgm_path, current_path.with_name(f"{current_path.stem}_bgm.mp4"), config.audio.volume)
        else:
            console.log("[yellow]未找到 BGM 文件，跳过音频混合。[/yellow]")

    if config.video.cover_export:
        cover_path = config.storage.cover_dir / f"{current_path.stem}.jpg"
        extract_cover(current_path, cover_path, config.video.cover_timecode)
        console.log(f"[green]封面帧已导出至：[/green]{cover_path}")

    return current_path


__all__ = [
    "adapt_vertical",
    "add_subtitles",
    "apply_watermark",
    "mix_bgm",
    "auto_postprocess",
]
