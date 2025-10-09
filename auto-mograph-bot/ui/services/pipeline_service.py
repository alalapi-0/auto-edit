"""与 runner 模块对接的流水线封装。"""
from __future__ import annotations

import uuid
from typing import Callable, Optional

from ..state import AppState, RuntimeTask
from ..utils import proc

LogCallback = Callable[[str], None]


class PipelineService:
    """负责触发生成任务并反馈日志。"""

    def __init__(self, state: AppState) -> None:
        self.state = state

    async def run_mvp(
        self,
        *,
        text: Optional[str] = None,
        seed: Optional[int] = None,
        log: Optional[LogCallback] = None,
    ) -> int:
        """运行 MVP CLI。"""

        profile = self.state.current_profile
        if not profile:
            raise RuntimeError("当前没有可用的 Profile")
        args = ["python", "-m", "runner.mvp_cli"]
        effective_text = text or profile.pipeline.text or "Auto mograph demo"
        args.extend(["--text", effective_text])
        if seed is None:
            seed = profile.pipeline.seed
        if seed is not None:
            args.extend(["--seed", str(seed)])
        return await self._execute(args, log)

    async def run_batch(self, *, count: int = 1, log: Optional[LogCallback] = None) -> int:
        """运行批量 CLI。"""

        args = ["python", "-m", "runner.cli", "--count", str(count)]
        return await self._execute(args, log)

    async def _execute(self, command: list[str], log: Optional[LogCallback]) -> int:
        task_id = uuid.uuid4().hex
        runtime_task = RuntimeTask(task_id=task_id, command=command)
        self.state.register_task(runtime_task)

        async def handle(line: str) -> None:
            self.state.update_task_log(task_id, line)
            if log:
                log(line)

        process = await proc.stream_process(
            command,
            stdout_handler=handle,
            stderr_handler=handle,
        )
        self.state.complete_task(task_id, process.returncode or 0)
        return process.returncode or 0


__all__ = ["PipelineService"]
