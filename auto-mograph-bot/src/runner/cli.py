"""命令行入口，提供批量生成与调度功能。"""

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console

from .job import GenerationJob
from .scheduler import GenerationScheduler

console = Console()


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="运行 Auto Mograph Bot 生成流水线")
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"), help="YAML 配置路径")
    parser.add_argument("--count", type=int, default=1, help="生成视频的数量")
    return parser.parse_args()


def main() -> None:
    """程序入口。"""

    args = parse_args()
    base_job = GenerationJob.from_config(args.config)
    config = base_job.config
    prompt_pool = base_job.prompt_pool

    def job_factory() -> GenerationJob:
        return GenerationJob(config=config, prompt_pool=prompt_pool)

    scheduler = GenerationScheduler(config=config, job_factory=job_factory)
    console.rule(f"批量生成 {args.count} 个任务")
    scheduler.run(args.count)


if __name__ == "__main__":
    main()
