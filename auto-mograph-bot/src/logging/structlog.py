"""结构化日志辅助工具。"""

from __future__ import annotations

import logging
from typing import Dict

_DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def get_logger(name: str = "auto_mograph") -> logging.Logger:
    """返回带有标准输出处理器的日志记录器。"""

    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_resource_snapshot(
    logger: logging.Logger,
    gpu_info: Dict[str, object],
    cpu_cores: int,
    requested: int,
    effective: int,
) -> None:
    """输出资源快照信息。"""

    logger.info(
        "Resource snapshot | GPU=%s | total=%sMB | free=%sMB | CPU cores=%s | requested=%s | effective=%s",
        gpu_info.get("name", "unknown"),
        gpu_info.get("total", 0),
        gpu_info.get("free", 0),
        cpu_cores,
        requested,
        effective,
    )


__all__ = ["get_logger", "log_resource_snapshot"]
