"""抖音/TikTok 官方或半官方 API Provider 占位实现。"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, Optional

from rich.console import Console

from ...config import PipelineConfig
from ..interfaces import DraftResult, UploadMetadata

console = Console()


class TikTokLikeAPIDraftUploader:
    """使用官方接口上传草稿的占位实现，具体参数需自行替换。"""

    provider_name = "api"

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.base_url: Optional[str] = config.uploader.extra.get("api_base") if config.uploader.extra else None
        self.token: Optional[str] = config.uploader.api_token

    def prepare_metadata(self, video_path: Path, metadata: UploadMetadata) -> UploadMetadata:
        console.log("[cyan]API Provider 正在预处理元数据（示例未做修改）。[/cyan]")
        return metadata

    def upload(self, video_path: Path, metadata: UploadMetadata) -> DraftResult:
        """调用官方接口上传草稿，当前仅返回占位结果。"""

        if not self.base_url or not self.token:
            return DraftResult(
                success=False,
                message="未配置官方 API 地址或 Token，无法启用 api provider。",
                provider=self.provider_name,
            )

        payload: Dict[str, object] = {
            "title": metadata.title,
            "desc": metadata.description,
            "tags": metadata.tags,
            "visibility": self.config.uploader.visibility,
        }
        headers = {"Authorization": f"Bearer {self.token}"}

        console.log(f"[yellow]示例将向 {self.base_url} 发送草稿请求（实际未执行）。[/yellow]")
        # 真实实现应上传视频文件，可采用分片/表单等方式
        time.sleep(0.2)
        return DraftResult(success=True, message="模拟调用官方接口完成", provider=self.provider_name)


__all__ = ["TikTokLikeAPIDraftUploader"]
