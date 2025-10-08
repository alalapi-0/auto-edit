"""上传模块路由器，根据配置选择合适的 Provider。"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from ..config import PipelineConfig
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
    prepared = uploader.prepare_metadata(video_path, metadata)
    try:
        return uploader.upload(video_path, prepared)
    except Exception as exc:  # noqa: BLE001
        console.log(f"[red]上传流程出现异常：{exc}[/red]")
        return DraftResult(success=False, message=str(exc), provider=getattr(uploader, "provider_name", "unknown"))


__all__ = ["build_uploader", "upload_video"]
