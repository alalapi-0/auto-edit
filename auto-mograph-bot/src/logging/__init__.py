"""日志工具模块。"""

from .structlog import get_logger, log_resource_snapshot

__all__ = ["get_logger", "log_resource_snapshot"]
