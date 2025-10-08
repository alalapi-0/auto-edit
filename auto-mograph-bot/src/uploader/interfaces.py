"""上传模块接口定义，仅提供草稿模拟功能。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Protocol

from rich.console import Console

console = Console()


@dataclass
class UploadMetadata:
    """上传草稿所需的基础信息。"""

    title: str
    description: str
    tags: list[str]
    extra: Dict[str, str]


@dataclass
class DraftResult:
    """上传结果，包含状态与提示。"""

    success: bool
    message: str
    draft_url: Optional[str] = None
    provider: Optional[str] = None


class Uploader(Protocol):
    """上传器通用协议。"""

    def prepare_metadata(self, video_path: Path, metadata: UploadMetadata) -> UploadMetadata:
        """可对标题、描述等进行再加工。"""

    def upload(self, video_path: Path, metadata: UploadMetadata) -> DraftResult:
        """执行上传，返回草稿结果。"""


class DummyUploader:
    """默认占位上传器，仅打印提示。"""

    provider_name = "none"

    def prepare_metadata(self, video_path: Path, metadata: UploadMetadata) -> UploadMetadata:
        console.log(f"[cyan]使用 DummyUploader 处理元数据：{metadata}[/cyan]")
        return metadata

    def upload(self, video_path: Path, metadata: UploadMetadata) -> DraftResult:
        console.log(f"[green]模拟草稿创建完成：{video_path}[/green]")
        return DraftResult(success=True, message="模拟草稿已保存（未上传）", provider=self.provider_name)


__all__ = ["UploadMetadata", "DraftResult", "Uploader", "DummyUploader"]
