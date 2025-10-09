"""用于调度器的文件锁实现。"""

from __future__ import annotations

import fcntl
import os
import time
from pathlib import Path
from typing import Optional


class FileLock:
    """简单的基于文件的互斥锁。"""

    def __init__(self, path: Optional[os.PathLike[str] | str] = None, timeout: float = 60.0) -> None:
        if path is None:
            path = "locks/gpu.lock"
        self.path = str(path)
        self.timeout = timeout
        directory = Path(self.path).parent
        directory.mkdir(parents=True, exist_ok=True)
        self._file = None

    def __enter__(self) -> "FileLock":
        start = time.time()
        self._file = open(self.path, "w", encoding="utf-8")
        while True:
            try:
                fcntl.flock(self._file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except BlockingIOError:
                if time.time() - start > self.timeout:
                    self._file.close()
                    raise TimeoutError("等待资源锁超时")
                time.sleep(0.5)

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: D401
        """释放锁并关闭文件。"""

        if self._file is not None:
            fcntl.flock(self._file, fcntl.LOCK_UN)
            self._file.close()
            self._file = None


__all__ = ["FileLock"]
