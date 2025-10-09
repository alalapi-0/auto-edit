"""GPU 与 CPU 资源探测工具。"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from typing import Dict

try:  # noqa: SIM105
    import torch  # type: ignore
except Exception:  # noqa: BLE001
    torch = None  # type: ignore[assignment]

try:  # noqa: SIM105
    import psutil  # type: ignore
except Exception:  # noqa: BLE001
    psutil = None  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)


def _parse_nvidia_smi(output: str) -> Dict[str, object]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        raise ValueError("nvidia-smi 未返回有效输出")
    first = lines[0]
    parts = [part.strip() for part in first.split(",")]
    if len(parts) < 3:
        matches = re.findall(r"(\d+)", first)
        if len(matches) >= 2:
            total, free = matches[:2]
            return {"total": int(total), "free": int(free), "name": "NVIDIA"}
        raise ValueError("无法解析 nvidia-smi 输出")
    total, free, name = parts[:3]
    return {"total": int(total), "free": int(free), "name": name or "NVIDIA"}


def get_gpu_info() -> Dict[str, object]:
    """返回首块 GPU 的显存信息，单位 MB。"""

    try:
        result = subprocess.run(  # noqa: S603
            [
                "nvidia-smi",
                "--query-gpu=memory.total,memory.free,name",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        info = _parse_nvidia_smi(result.stdout)
        return info
    except Exception as exc:  # noqa: BLE001
        LOGGER.debug("nvidia-smi 调用失败，尝试使用 PyTorch 读取 GPU 信息", exc_info=exc)

    if torch is not None and hasattr(torch, "cuda") and torch.cuda.is_available():  # type: ignore[attr-defined]
        props = torch.cuda.get_device_properties(0)
        total = props.total_memory // (1024 * 1024)
        used = torch.cuda.memory_allocated(0) // (1024 * 1024)
        return {"total": int(total), "free": int(total - used), "name": props.name}

    return {"total": 0, "free": 0, "name": "CPU"}


def get_cpu_cores() -> int:
    """返回物理 CPU 核心数，获取失败时退化为 1。"""

    if psutil is not None:
        cores = psutil.cpu_count(logical=False)
        if cores:
            return int(cores)
    fallback = os.cpu_count() or 1
    return int(fallback)


__all__ = ["get_gpu_info", "get_cpu_cores"]
