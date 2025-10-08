"""小红书 Web 自动化上传 Provider 占位实现。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

from rich.console import Console

from ...config import PipelineConfig
from ..interfaces import DraftResult, UploadMetadata

console = Console()


class XiaohongshuWebUploader:
    """基于 Playwright 的浏览器自动化草稿上传流程。"""

    provider_name = "web"

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.cookie_path: Optional[Path] = config.uploader.cookie_path
        self.log_dir = config.scheduler.log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.visibility = config.uploader.visibility

    def prepare_metadata(self, video_path: Path, metadata: UploadMetadata) -> UploadMetadata:
        console.log("[cyan]Web Provider 将标题截断以防止超长。[/cyan]")
        metadata.title = metadata.title[:30]
        return metadata

    async def _upload_async(self, video_path: Path, metadata: UploadMetadata) -> DraftResult:
        from playwright.async_api import async_playwright  # 延迟导入，避免非必需依赖

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            if self.cookie_path and self.cookie_path.exists():
                cookies = json.loads(self.cookie_path.read_text(encoding="utf-8"))
                await context.add_cookies(cookies)
            page = await context.new_page()
            await page.goto("https://creator.xiaohongshu.com/creation")
            await page.wait_for_timeout(2000)
            await page.set_input_files("input[type=file]", str(video_path))
            await page.fill("textarea[placeholder='写点什么...']", metadata.description)
            await page.fill("input[placeholder='添加标题']", metadata.title)
            if metadata.tags:
                await page.fill("input[placeholder='添加话题']", " ".join(metadata.tags))
            await page.wait_for_timeout(1000)
            screenshot_path = self.log_dir / f"xiaohongshu_preview_{video_path.stem}.png"
            await page.screenshot(path=str(screenshot_path))
            har_path = self.log_dir / f"xiaohongshu_{video_path.stem}.har"
            await context.tracing.start(title="xiaohongshu-upload", screenshots=True, snapshots=True)
            await page.wait_for_timeout(500)
            await context.tracing.stop(path=str(har_path))
            await browser.close()
        return DraftResult(success=True, message="已模拟 Web 自动化流程", provider=self.provider_name, draft_url=str(screenshot_path))

    def upload(self, video_path: Path, metadata: UploadMetadata) -> DraftResult:
        if not self.cookie_path or not self.cookie_path.exists():
            return DraftResult(
                success=False,
                message="未找到 Cookie 文件，无法执行 Web 自动化。",
                provider=self.provider_name,
            )
        try:
            return asyncio.run(self._upload_async(video_path, metadata))
        except Exception as exc:  # noqa: BLE001
            error_log = self.log_dir / f"xiaohongshu_error_{video_path.stem}.log"
            error_log.write_text(str(exc), encoding="utf-8")
            console.log(f"[red]Web 上传失败：{exc}[/red]")
            return DraftResult(success=False, message=str(exc), provider=self.provider_name)


__all__ = ["XiaohongshuWebUploader"]
