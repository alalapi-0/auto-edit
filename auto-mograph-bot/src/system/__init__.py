"""系统资源探测模块。"""

from .gpu_probe import get_cpu_cores, get_gpu_info

__all__ = ["get_cpu_cores", "get_gpu_info"]
