"""基于 Appium 的移动端自动化上传 Provider 占位实现。"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from ...config import PipelineConfig
from ..interfaces import DraftResult, UploadMetadata

console = Console()


class AndroidAppiumUploader:
    """通过 Android 模拟器执行上传草稿的占位实现。"""

    provider_name = "appium"

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.server = config.uploader.appium_server or "http://127.0.0.1:4723/wd/hub"
        self.device_name = config.uploader.device_name or "Android Emulator"
        self.platform_version = config.uploader.extra.get("platformVersion") if config.uploader.extra else None
        self.app_package = config.uploader.extra.get("appPackage") if config.uploader.extra else None
        self.app_activity = config.uploader.extra.get("appActivity") if config.uploader.extra else None

    def prepare_metadata(self, video_path: Path, metadata: UploadMetadata) -> UploadMetadata:
        console.log("[cyan]Appium Provider 会将标签列表格式化为字符串。[/cyan]")
        metadata.extra["joined_tags"] = ",".join(metadata.tags)
        return metadata

    def upload(self, video_path: Path, metadata: UploadMetadata) -> DraftResult:
        try:
            from appium import webdriver  # 延迟导入
        except Exception as exc:  # noqa: BLE001
            return DraftResult(success=False, message=f"未安装 appium-python-client: {exc}", provider=self.provider_name)

        desired_capabilities = {
            "platformName": "Android",
            "deviceName": self.device_name,
            "appPackage": self.app_package or "com.ss.android.ugc.aweme",
            "appActivity": self.app_activity or "com.ss.android.ugc.aweme.main.MainActivity",
            "noReset": True,
        }
        if self.platform_version:
            desired_capabilities["platformVersion"] = self.platform_version

        console.log(f"[cyan]连接 Appium Server: {self.server}[/cyan]")
        try:
            driver = webdriver.Remote(self.server, desired_capabilities)
        except Exception as exc:  # noqa: BLE001
            return DraftResult(success=False, message=str(exc), provider=self.provider_name)

        try:
            console.log("[yellow]以下步骤需根据实际 App UI 自行实现：[/yellow]")
            console.log("1. 将视频推送到模拟器共享目录")
            console.log("2. 在应用内点击发布入口 -> 选择视频 -> 编辑 -> 保存草稿")
            console.log(f"视频路径：{video_path}")
            return DraftResult(success=True, message="模拟 Appium 上传已完成（示意）", provider=self.provider_name)
        finally:
            driver.quit()


__all__ = ["AndroidAppiumUploader"]
