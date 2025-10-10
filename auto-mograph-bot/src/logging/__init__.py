"""日志工具模块。"""

from .structlog import (
    get_logger,
    init_logging,
    log_event,
    log_exception,
    log_resource_snapshot,
)

__all__ = [
    "get_logger",
    "init_logging",
    "log_event",
    "log_exception",
    "log_resource_snapshot",
]
