"""云厂商占位 Provider，实现 UI 流程演示。"""
from __future__ import annotations

import asyncio
import random
from typing import Any, Dict

from .base import BaseProvider, VPSInstance


class PlaceholderProvider(BaseProvider):
    """仅用于演示的占位 Provider。"""

    name = "placeholder"
    display_name = "占位 Provider"

    async def create(self, options: Dict[str, Any]) -> VPSInstance:
        await asyncio.sleep(0.5)
        identifier = f"fake-{random.randint(1000, 9999)}"
        metadata = {"api_key": options.get("api_key", ""), "region": options.get("region", "auto")}
        return VPSInstance(identifier=identifier, status="provisioned", metadata=metadata)

    async def destroy(self, identifier: str) -> None:
        await asyncio.sleep(0.2)

    async def exec(self, identifier: str, command: str) -> str:
        await asyncio.sleep(0.1)
        return f"[{identifier}] 模拟执行指令: {command}"


__all__ = ["PlaceholderProvider"]
