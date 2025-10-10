"""上传模块路由器，根据配置选择合适的 Provider。"""

from __future__ import annotations

import time
from pathlib import Path

from rich.console import Console

from ..config import PipelineConfig
from ..logging.structlog import log_event, log_exception
from .interfaces import DraftResult, DummyUploader, UploadMetadata, Uploader
from .providers.android_appium import AndroidAppiumUploader
from .providers.tiktok_like_api import TikTokLikeAPIDraftUploader
from .providers.xiaohongshu_web import XiaohongshuWebUploader

console = Console()


def build_uploader(config: PipelineConfig) -> Uploader:
    """根据配置返回对应的上传实现。"""

    provider = config.uploader.provider
    if provider == "web":
        return XiaohongshuWebUploader(config)
    if provider == "appium":
        return AndroidAppiumUploader(config)
    if provider == "api":
        return TikTokLikeAPIDraftUploader(config)
    return DummyUploader()


def upload_video(config: PipelineConfig, video_path: Path, metadata: UploadMetadata) -> DraftResult:
    """统一上传入口：准备元数据并执行上传。"""

    uploader = build_uploader(config)
    provider_name = getattr(uploader, "provider_name", config.uploader.provider or "unknown")
    start = time.time()
    log_event(
        "upload_start",
        platform=config.uploader.target,
        provider=provider_name,
        file=str(video_path),
    )
    prepared = uploader.prepare_metadata(video_path, metadata)
    log_event(
        "upload_metadata_prepared",
        platform=config.uploader.target,
        provider=provider_name,
        file=str(video_path),
    )
    try:
        result = uploader.upload(video_path, prepared)
        elapsed_ms = int((time.time() - start) * 1000)
        log_event(
            "upload_success",
            platform=config.uploader.target,
            provider=provider_name,
            file=str(video_path),
            elapsed_ms=elapsed_ms,
            draft_url=result.draft_url,
        )
        return result
    except Exception as exc:  # noqa: BLE001
        console.log(f"[red]上传流程出现异常：{exc}[/red]")
        elapsed_ms = int((time.time() - start) * 1000)
        log_exception(
            "upload_fail",
            exc,
            platform=config.uploader.target,
            provider=provider_name,
            file=str(video_path),
            elapsed_ms=elapsed_ms,
        )
        return DraftResult(success=False, message=str(exc), provider=provider_name)


__all__ = ["build_uploader", "upload_video"]
