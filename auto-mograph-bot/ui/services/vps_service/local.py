"""本地机 Provider 实现。"""
from __future__ import annotations

from typing import Any, Dict

from .base import BaseProvider, VPSInstance


class LocalProvider(BaseProvider):
    """直接在当前机器运行任务。"""

    name = "local"
    display_name = "本地机器"

    async def create(self, options: Dict[str, Any]) -> VPSInstance:
        return VPSInstance(identifier="local", status="ready", metadata={"cwd": options.get("cwd", "./")})

    async def destroy(self, identifier: str) -> None:
        # 本地 provider 无需实际销毁
        return None

    async def exec(self, identifier: str, command: str) -> str:
        return f"在 {identifier} 上执行: {command}"


__all__ = ["LocalProvider"]
