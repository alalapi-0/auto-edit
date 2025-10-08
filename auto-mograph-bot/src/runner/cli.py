"""Command line entry point for Auto Mograph Bot."""

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console

from .job import GenerationJob

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Auto Mograph Bot pipeline")
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"), help="Path to YAML config")
    parser.add_argument("--count", type=int, default=1, help="Number of jobs to run")
    parser.add_argument("--output", type=Path, default=Path("outputs"), help="Output directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    job = GenerationJob.from_config(args.config)
    for index in range(args.count):
        console.rule(f"Job {index + 1}/{args.count}")
        job.run(args.output / f"job_{index + 1}")


if __name__ == "__main__":
    main()
