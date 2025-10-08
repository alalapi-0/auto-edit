"""Utility helpers to interact with FFmpeg."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterable, List

from rich.console import Console

console = Console()


def ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("FFmpeg binary not found. Please install FFmpeg and ensure it is on PATH.")


def run_ffmpeg(command: List[str]) -> None:
    ensure_ffmpeg_available()
    console.log("Running FFmpeg command", " ".join(command))
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        console.log(result.stderr)
        raise RuntimeError(f"FFmpeg command failed with code {result.returncode}")
    console.log(result.stdout)


def concat_videos(inputs: Iterable[Path], output: Path, reencode: bool = False) -> Path:
    """Concatenate videos using FFmpeg."""

    output.parent.mkdir(parents=True, exist_ok=True)
    file_list = output.with_suffix(".txt")
    with file_list.open("w", encoding="utf-8") as fp:
        for item in inputs:
            fp.write(f"file '{item.as_posix()}'\n")

    command = [
        "ffmpeg",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(file_list),
    ]
    if reencode:
        command.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "18"])
    else:
        command.extend(["-c", "copy"])
    command.append(str(output))

    run_ffmpeg(command)
    file_list.unlink(missing_ok=True)
    return output


__all__ = ["concat_videos", "ensure_ffmpeg_available"]
