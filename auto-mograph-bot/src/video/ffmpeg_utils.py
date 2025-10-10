"""FFmpeg 调用工具集，封装常用的编码、音频混合与封面导出逻辑。"""

from __future__ import annotations

import os
import random
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from rich.console import Console

from ..logging.structlog import log_event, log_exception

console = Console()

_FFMPEG_RETRY_CFG: Dict[str, object] = {
    "max_attempts": 1,
    "backoff_factor": 1.0,
    "jitter_ms": 0,
    "enabled": False,
    "retryable_exit_codes": [],
}


def configure_ffmpeg_retry(settings: object) -> None:
    """同步配置中的 FFmpeg 重试策略。"""

    global _FFMPEG_RETRY_CFG
    if settings is None:
        return
    if hasattr(settings, "model_dump"):
        data = settings.model_dump()
    elif isinstance(settings, dict):
        data = settings
    else:
        data = dict(settings)
    ffmpeg_cfg = data.get("ffmpeg", {}) if isinstance(data, dict) else {}
    updated = {
        "max_attempts": int(data.get("max_attempts", 1)),
        "backoff_factor": float(data.get("backoff_factor", 1.0)),
        "jitter_ms": int(data.get("jitter_ms", 0)),
        "enabled": bool(ffmpeg_cfg.get("enabled", False)),
        "retryable_exit_codes": list(ffmpeg_cfg.get("retryable_exit_codes", [])),
    }
    _FFMPEG_RETRY_CFG = updated
    log_event("retry_config_updated", component="ffmpeg", config=updated)


def _normalize_retry_cfg(raw: Optional[Dict[str, object]]) -> Dict[str, object]:
    if not raw:
        return dict(_FFMPEG_RETRY_CFG)
    cfg = dict(raw)
    return {
        "max_attempts": max(1, int(cfg.get("max_attempts", _FFMPEG_RETRY_CFG["max_attempts"]))),
        "backoff_factor": max(1.0, float(cfg.get("backoff_factor", _FFMPEG_RETRY_CFG["backoff_factor"]))),
        "jitter_ms": max(0, int(cfg.get("jitter_ms", _FFMPEG_RETRY_CFG["jitter_ms"]))),
        "enabled": bool(cfg.get("enabled", _FFMPEG_RETRY_CFG["enabled"])),
        "retryable_exit_codes": list(cfg.get("retryable_exit_codes", _FFMPEG_RETRY_CFG["retryable_exit_codes"])),
    }


def _tail_text(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def classify_ffmpeg(stderr: str, code: int) -> Tuple[str, str]:
    """根据 FFmpeg 输出推断错误类别与修复建议。"""

    message = (stderr or "").lower()
    if code == 127 or "command not found" in message:
        return "no_ffmpeg", "确认已安装 FFmpeg 并在 PATH 中可用"
    if "no such file or directory" in message or "unable to open" in message:
        return "file_not_found", "检查输入输出路径是否正确存在"
    if "permission denied" in message:
        return "permission", "检查输出目录及文件权限"
    if "no space left" in message or "disk full" in message:
        return "disk_full", "清理磁盘空间或调整输出目录"
    if "codec not found" in message or "unknown encoder" in message:
        return "codec_missing", "安装所需编解码器或修改编码参数"
    if "device or resource busy" in message or "resource temporarily unavailable" in message:
        return "resource_busy", "确认输出文件未被占用或稍后重试"
    if "broken pipe" in message or "ePIPE" in message:
        return "broken_pipe", "检查上游数据流或管道写入是否中断"
    if "connection timed out" in message or "timed out" in message:
        return "timeout", "检查网络/IO 条件或调高超时时间"
    if "input/output error" in message:
        return "io_error", "检查磁盘健康状态或更换输出位置"
    return "unknown", "查看 stderr 详情或命令参数以进一步排查"


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


def run_ffmpeg(command: Sequence[str], *, _retry_cfg: Optional[Dict[str, object]] = None) -> None:
    """运行 FFmpeg 命令并在失败时执行分类与重试。"""

    cfg = _normalize_retry_cfg(_retry_cfg)
    attempts = 1
    if cfg.get("enabled"):
        attempts = max(1, int(cfg.get("max_attempts", 1)))
    delay = 1.0
    cmd_str = " ".join(command)

    for attempt in range(1, attempts + 1):
        log_event("ffmpeg_start", command=cmd_str, attempt=attempt, max_attempts=attempts)
        console.log("[cyan]执行 FFmpeg：[/cyan]" + cmd_str)
        start = time.time()
        try:
            process = subprocess.run(command, check=False, capture_output=True, text=True)
        except FileNotFoundError as err:
            elapsed_ms = int((time.time() - start) * 1000)
            category, hint = "no_ffmpeg", "确认已安装 FFmpeg 并在 PATH 中可用"
            log_exception(
                "ffmpeg_fail",
                err,
                command=cmd_str,
                attempt=attempt,
                elapsed_ms=elapsed_ms,
                category=category,
                hint=hint,
            )
            raise RuntimeError("未找到 FFmpeg 可执行文件") from err

        stdout = process.stdout or ""
        stderr = process.stderr or ""
        code = process.returncode
        elapsed_ms = int((time.time() - start) * 1000)

        if stdout.strip():
            console.log(stdout)

        if code == 0:
            log_event("ffmpeg_success", command=cmd_str, attempt=attempt, elapsed_ms=elapsed_ms)
            return

        console.log(f"[red]FFmpeg 执行失败：{stderr}[/red]")
        category, hint = classify_ffmpeg(stderr, code)
        error = RuntimeError(f"FFmpeg 命令失败，退出码 {code}")
        log_exception(
            "ffmpeg_fail",
            error,
            command=cmd_str,
            attempt=attempt,
            elapsed_ms=elapsed_ms,
            category=category,
            hint=hint,
            code=code,
            stderr=_tail_text(stderr),
        )

        retryable_codes = set(cfg.get("retryable_exit_codes", []))
        retryable_categories = {"timeout", "resource_busy", "broken_pipe", "io_error"}
        should_retry = (
            cfg.get("enabled")
            and attempt < attempts
            and (code in retryable_codes or category in retryable_categories)
        )

        if should_retry:
            jitter_ms = int(cfg.get("jitter_ms", 0))
            jitter = random.randint(0, jitter_ms) / 1000.0 if jitter_ms else 0.0
            sleep_seconds = delay + jitter
            log_event(
                "ffmpeg_retry",
                command=cmd_str,
                attempt=attempt,
                next_delay_ms=int(sleep_seconds * 1000),
                category=category,
                hint=hint,
                code=code,
            )
            time.sleep(sleep_seconds)
            delay *= float(cfg.get("backoff_factor", 1.0))
            continue

        raise error

    raise RuntimeError("FFmpeg 命令多次重试后仍失败")


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
    "configure_ffmpeg_retry",
]
