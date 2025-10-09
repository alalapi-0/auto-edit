"""上传流程服务封装。"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, Optional

from ..state import AppState


@dataclass
class UploadResult:
    """上传结果。"""

    success: bool
    message: str
    payload: Optional[Dict[str, str]] = None


class UploaderService:
    """根据配置触发上传动作。"""

    def __init__(self, state: AppState) -> None:
        self.state = state

    async def simulate_upload(self) -> UploadResult:
        """执行模拟上传流程，用于 UI 测试。"""

        profile = self.state.current_profile
        if not profile:
            raise RuntimeError("当前没有可用的 Profile")
        await asyncio.sleep(0.5)
        payload = {
            "platform": profile.uploader.platform,
            "provider": profile.uploader.provider,
            "storage_state_path": profile.uploader.storage_state_path or "<未配置>",
        }
        message = (
            "模拟上传成功" if profile.uploader.provider != "none" else "未启用上传，跳过"
        )
        return UploadResult(success=True, message=message, payload=payload)


__all__ = ["UploaderService", "UploadResult"]
