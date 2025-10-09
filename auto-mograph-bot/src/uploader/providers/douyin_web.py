"""Douyin web uploader that consumes encrypted storage states."""

from __future__ import annotations

import asyncio
import io
from pathlib import Path

from rich.console import Console

from ...config import PipelineConfig
from ..interfaces import DraftResult, UploadMetadata
from ui.services.secrets_service import (
    SecretsError,
    SecretsExpiredError,
    SecretsService,
)

console = Console()


class DouyinWebUploader:
    """Playwright-based placeholder uploader for Douyin web drafts."""

    provider_name = "web"

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.log_dir = config.scheduler.log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.visibility = config.uploader.visibility
        self.secret_name = "douyin_state"
        self.secrets_service = SecretsService()

    def prepare_metadata(self, video_path: Path, metadata: UploadMetadata) -> UploadMetadata:
        console.log("[cyan]Douyin Web Provider 正在准备元数据。[/cyan]")
        return metadata

    async def _upload_async(
        self, video_path: Path, metadata: UploadMetadata, state_bytes: bytes
    ) -> DraftResult:
        from playwright.async_api import async_playwright  # 延迟导入，避免非必需依赖

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=io.BytesIO(state_bytes))
            page = await context.new_page()
            await page.goto("https://creator.douyin.com/creator-micro/creation/content/upload")
            await page.wait_for_timeout(500)
            await browser.close()
        return DraftResult(
            success=True,
            message="已模拟 Douyin Web 自动化流程",
            provider=self.provider_name,
        )

    def upload(self, video_path: Path, metadata: UploadMetadata) -> DraftResult:
        try:
            state_bytes = self.secrets_service.load(self.secret_name)
        except SecretsExpiredError as exc:
            self._log_secret_issue(exc)
            raise
        except SecretsError as exc:
            self._log_secret_issue(exc)
            raise
        try:
            return asyncio.run(self._upload_async(video_path, metadata, state_bytes))
        except Exception as exc:  # noqa: BLE001
            error_log = self.log_dir / f"douyin_error_{video_path.stem}.log"
            error_log.write_text(str(exc), encoding="utf-8")
            console.log(f"[red]Douyin Web 上传失败：{exc}[/red]")
            return DraftResult(success=False, message=str(exc), provider=self.provider_name)

    def _log_secret_issue(self, exc: Exception) -> None:
        error_log = self.log_dir / "douyin_secrets_error.log"
        error_log.write_text(str(exc), encoding="utf-8")
        console.log(f"[red]Douyin 登录态加载失败：{exc}[/red]")


__all__ = ["DouyinWebUploader"]
