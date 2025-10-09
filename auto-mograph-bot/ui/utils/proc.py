"""子进程运行与日志转发工具。"""
from __future__ import annotations

import asyncio
from asyncio.subprocess import Process
from pathlib import Path
from typing import Awaitable, Callable, Optional, Sequence

LogHandler = Callable[[str], Awaitable[None] | None]


async def _read_stream(stream, handler: LogHandler) -> None:
    """逐行读取流并传递给 handler。"""

    while True:
        line = await stream.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="ignore").rstrip("\n")
        result = handler(text)
        if asyncio.iscoroutine(result):
            await result


async def stream_process(
    command: Sequence[str],
    *,
    cwd: Optional[Path | str] = None,
    env: Optional[dict[str, str]] = None,
    stdout_handler: Optional[LogHandler] = None,
    stderr_handler: Optional[LogHandler] = None,
) -> Process:
    """运行子进程并将输出流向 UI。"""

    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    handlers = []
    if stdout_handler and process.stdout:
        handlers.append(asyncio.create_task(_read_stream(process.stdout, stdout_handler)))
    if stderr_handler and process.stderr:
        handlers.append(asyncio.create_task(_read_stream(process.stderr, stderr_handler)))

    if handlers:
        await asyncio.wait(handlers)

    await process.wait()
    return process


async def run_and_capture(
    command: Sequence[str],
    *,
    cwd: Optional[Path | str] = None,
    env: Optional[dict[str, str]] = None,
) -> tuple[int, str]:
    """运行命令并返回退出码与输出文本。"""

    buffer: list[str] = []

    async def append(line: str) -> None:
        buffer.append(line)

    process = await stream_process(
        command,
        cwd=cwd,
        env=env,
        stdout_handler=append,
        stderr_handler=append,
    )
    return process.returncode or 0, "\n".join(buffer)


__all__ = ["stream_process", "run_and_capture"]
