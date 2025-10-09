"""VPS Provider 抽象定义。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class VPSInstance:
    """VPS 实例元数据。"""

    identifier: str
    status: str
    metadata: Dict[str, Any]


class BaseProvider:
    """VPS Provider 接口。"""

    name: str = "base"
    display_name: str = "Base Provider"

    async def create(self, options: Dict[str, Any]) -> VPSInstance:  # pragma: no cover - 接口
        raise NotImplementedError

    async def destroy(self, identifier: str) -> None:  # pragma: no cover - 接口
        raise NotImplementedError

    async def exec(self, identifier: str, command: str) -> str:  # pragma: no cover
        raise NotImplementedError


__all__ = ["BaseProvider", "VPSInstance"]
