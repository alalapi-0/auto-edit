"""桌面应用入口。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow
from .state import AppState


def load_stylesheet(path: Path) -> str:
    """读取 QSS 样式表。"""

    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auto Mograph 桌面 UI")
    parser.add_argument("--no-wizard", action="store_true", help="跳过首次启动向导")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = create_argument_parser().parse_args(argv)
    app = QApplication(sys.argv)
    state = AppState()
    if args.no_wizard:
        flag = Path("profiles/.first_run_done")
        if not flag.exists():
            flag.touch()
    window = MainWindow(state, show_wizard=not args.no_wizard)
    stylesheet = load_stylesheet(Path("ui/qss/app.qss"))
    if stylesheet:
        app.setStyleSheet(stylesheet)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
