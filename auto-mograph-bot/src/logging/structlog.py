"""结构化日志辅助工具，负责输出 JSONL 事件。"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import traceback
from typing import Any, Dict, Optional

_DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_FALLBACK_LOGGER_NAME = "auto_mograph"
_WRITE_LOCK = threading.Lock()
_LOG_PATH: Optional[str] = None


def _ensure_fallback_logger() -> logging.Logger:
    """确保存在一个标准输出日志记录器，用于未初始化时的回退。"""

    logger = logging.getLogger(_FALLBACK_LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def _json_default(value: Any) -> Any:
    """为 JSON 序列化提供兜底转换。"""

    if isinstance(value, Exception):
        return str(value)
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:  # noqa: BLE001
            return str(value)
    return str(value)


def init_logging(jsonl_path: str) -> None:
    """初始化结构化日志输出位置。"""

    global _LOG_PATH
    if not jsonl_path:
        _LOG_PATH = None
        return
    directory = os.path.dirname(jsonl_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    _LOG_PATH = jsonl_path


def _write_record(record: Dict[str, Any]) -> None:
    """写入单行 JSON 记录，必要时退回到标准日志。"""

    if _LOG_PATH:
        line = json.dumps(record, ensure_ascii=False, default=_json_default)
        with _WRITE_LOCK:
            with open(_LOG_PATH, "a", encoding="utf-8") as fp:
                fp.write(line + "\n")
    else:
        fallback = _ensure_fallback_logger()
        fallback.info(json.dumps(record, ensure_ascii=False, default=_json_default))


def log_event(event: str, **kwargs: Any) -> None:
    """输出结构化事件日志。"""

    record: Dict[str, Any] = {"event": event, "ts": time.time()}
    record.update(kwargs)
    _write_record(record)


def log_exception(event: str, err: Exception, **kwargs: Any) -> None:
    """输出包含异常信息与堆栈的结构化日志。"""

    trace = traceback.format_exc()
    log_event(event, error=str(err), traceback=trace, **kwargs)


def get_logger(name: str = _FALLBACK_LOGGER_NAME) -> logging.Logger:
    """兼容旧接口，返回标准输出日志记录器。"""

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
    """输出资源快照信息，同时写入结构化日志。"""

    message = (
        "Resource snapshot | GPU=%s | total=%sMB | free=%sMB | CPU cores=%s | requested=%s | effective=%s"
        % (
            gpu_info.get("name", "unknown"),
            gpu_info.get("total", 0),
            gpu_info.get("free", 0),
            cpu_cores,
            requested,
            effective,
        )
    )
    logger.info(message)
    log_event(
        "resource_snapshot",
        gpu=gpu_info,
        cpu_cores=cpu_cores,
        requested_concurrency=requested,
        effective_concurrency=effective,
    )


__all__ = [
    "get_logger",
    "init_logging",
    "log_event",
    "log_exception",
    "log_resource_snapshot",
]
