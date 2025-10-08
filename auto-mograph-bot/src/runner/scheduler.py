"""批量调度模块，负责任务重试、索引写入与去重。"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional, Set

from rich.console import Console

from ..config import PipelineConfig
from .job import GenerationJob, JobResult

console = Console()


class GenerationScheduler:
    """批量任务调度器，支持失败重试与产物索引。"""

    def __init__(self, config: PipelineConfig, job_factory: Callable[[], GenerationJob]) -> None:
        self.config = config
        self.job_factory = job_factory
        self.index_file = config.scheduler.index_file
        self.completed_hashes: Set[str] = self._load_existing_hashes()
        self.index_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_existing_hashes(self) -> Set[str]:
        hashes: Set[str] = set()
        if not self.index_file.exists():
            return hashes
        with self.index_file.open("r", encoding="utf-8") as fp:
            for line in fp:
                try:
                    record = json.loads(line)
                    if "hash" in record:
                        hashes.add(record["hash"])
                except json.JSONDecodeError:
                    continue
        return hashes

    def _append_index(self, result: JobResult) -> None:
        record: Dict[str, object] = {
            "prompt": result.prompt.prompt,
            "title": result.prompt.title,
            "tags": result.prompt.tags,
            "seed": result.prompt.seed,
            "hash": result.file_hash,
            "video_path": str(result.final_video_path),
            "duration": result.duration,
            "sd_backend": self.config.sd.backend,
            "video_backend": self.config.animate.backend,
            "upload": {
                "success": result.upload_result.success,
                "message": result.upload_result.message,
                "provider": result.upload_result.provider,
                "draft_url": result.upload_result.draft_url,
            },
        }
        with self.index_file.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _run_single(self, attempt: int) -> Optional[JobResult]:
        job = self.job_factory()
        try:
            result = job.run()
        except Exception as exc:  # noqa: BLE001
            console.log(f"[red]任务执行失败（第 {attempt} 次）：{exc}[/red]")
            time.sleep(self.config.scheduler.cooldown_sec)
            return None

        if result.file_hash and result.file_hash in self.completed_hashes:
            console.log("[yellow]检测到重复产物哈希，跳过索引写入。[/yellow]")
            return result

        if result.file_hash:
            self.completed_hashes.add(result.file_hash)
        self._append_index(result)
        return result

    def run(self, count: int) -> List[JobResult]:
        """按照配置批量执行任务。"""

        results: List[JobResult] = []
        max_retries = self.config.scheduler.max_retries
        concurrency = max(1, self.config.scheduler.concurrency)
        if concurrency > 1:
            console.log("[yellow]当前骨架未实现真正并发，已将并发度降至 1。[/yellow]")
            concurrency = 1

        pending = list(range(count))
        while pending:
            batch = pending[:concurrency]
            del pending[:concurrency]
            futures = []
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                for _ in batch:
                    futures.append(executor.submit(self._run_with_retry, max_retries))
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        results.append(result)
        return results

    def _run_with_retry(self, max_retries: int) -> Optional[JobResult]:
        for attempt in range(1, max_retries + 2):
            outcome = self._run_single(attempt)
            if outcome:
                return outcome
        return None


__all__ = ["GenerationScheduler"]
