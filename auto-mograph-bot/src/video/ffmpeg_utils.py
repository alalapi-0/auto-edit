"""FFmpeg 调用工具集，封装常用的编码、音频混合与封面导出逻辑。"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Sequence

from rich.console import Console

console = Console()


def ensure_ffmpeg_available(explicit_path: Optional[str] = None) -> str:
    """确认 FFmpeg 可用并返回可执行路径。"""

    if explicit_path:
        return explicit_path
    env_path = os.getenv("FFMPEG_PATH")
    if env_path:
        return env_path
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError("未找到 FFmpeg 可执行文件，请安装后将其加入 PATH。")
    return ffmpeg_path


def run_ffmpeg(command: Sequence[str]) -> None:
    """运行 FFmpeg 命令并输出日志。"""

    console.log("[cyan]执行 FFmpeg：[/cyan]" + " ".join(command))
    process = subprocess.run(command, check=False, capture_output=True, text=True)
    if process.stdout:
        console.log(process.stdout)
    if process.returncode != 0:
        console.log(f"[red]FFmpeg 执行失败：{process.stderr}[/red]")
        raise RuntimeError(f"FFmpeg 命令失败，退出码 {process.returncode}")


def encode_image_sequence(
    frames_pattern: str,
    output_path: Path,
    fps: int,
    width: int,
    height: int,
    crf: int,
    preset: str,
    bitrate: Optional[str],
    audio_path: Optional[Path] = None,
    audio_bitrate: str = "192k",
) -> Path:
    """将序列帧编码为 H.264 MP4。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command: List[str] = [
        ensure_ffmpeg_available(),
        "-y",
        "-framerate",
        str(fps),
        "-i",
        frames_pattern,
        "-s",
        f"{width}x{height}",
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
    ]
    if bitrate:
        command.extend(["-b:v", bitrate])
    if audio_path:
        command.extend(["-i", str(audio_path), "-c:a", "aac", "-b:a", audio_bitrate])
    else:
        command.extend(["-an"])
    command.append(str(output_path))

    run_ffmpeg(command)
    return output_path


def mux_audio(video_path: Path, audio_path: Path, output_path: Path, audio_bitrate: str = "192k") -> Path:
    """为视频重新混音音频轨。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ensure_ffmpeg_available(),
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        audio_bitrate,
        str(output_path),
    ]
    run_ffmpeg(command)
    return output_path


def extract_cover(video_path: Path, cover_path: Path, timecode: float = 0.0) -> Path:
    """从视频中截取封面帧。"""

    cover_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ensure_ffmpeg_available(),
        "-y",
        "-ss",
        str(timecode),
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        str(cover_path),
    ]
    run_ffmpeg(command)
    return cover_path


def create_placeholder_clip(
    output_path: Path,
    width: int,
    height: int,
    duration: float,
    fps: int,
    text: str = "Auto Mograph Bot",
) -> Path:
    """使用 FFmpeg 生成单色占位视频，方便示例流程。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ensure_ffmpeg_available(),
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x1a1a1a:s={width}x{height}:r={fps}:d={duration}",
        "-vf",
        "drawtext=text='" + text.replace("'", "\\'") + "':fontcolor=white:fontsize=64:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "18",
        str(output_path),
    ]
    run_ffmpeg(command)
    return output_path


__all__ = [
    "ensure_ffmpeg_available",
    "run_ffmpeg",
    "encode_image_sequence",
    "mux_audio",
    "extract_cover",
    "create_placeholder_clip",
]
