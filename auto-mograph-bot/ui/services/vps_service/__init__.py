"""VPS Provider 注册表。"""
from __future__ import annotations

from typing import Dict

from .base import BaseProvider
from .local import LocalProvider
from .placeholder import PlaceholderProvider


def get_providers() -> Dict[str, BaseProvider]:
    """返回可用 Provider 实例字典。"""

    providers: Dict[str, BaseProvider] = {
        LocalProvider.name: LocalProvider(),
        PlaceholderProvider.name: PlaceholderProvider(),
    }
    return providers


__all__ = ["get_providers", "BaseProvider", "LocalProvider", "PlaceholderProvider"]
