"""首次启动向导。"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QStackedLayout,
    QWidget,
    QFormLayout,
    QLineEdit,
    QFileDialog,
)

from ...state import AppState


class FirstRunWizard(QDialog):
    """简单的首次启动引导。"""

    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("首次启动向导")
        self.state = state

        self.layout_root = QVBoxLayout()
        self.stack = QStackedLayout()

        self.next_button = QPushButton("下一步", self)
        self.prev_button = QPushButton("上一步", self)
        self.finish_button = QPushButton("完成", self)
        self.finish_button.setEnabled(False)

        self._build_step_checks()
        self._build_step_database()
        self._build_step_storage()

        controls = QVBoxLayout()
        controls.addWidget(self.prev_button)
        controls.addWidget(self.next_button)
        controls.addWidget(self.finish_button)

        self.layout_root.addLayout(self.stack)
        self.layout_root.addLayout(controls)
        self.setLayout(self.layout_root)

        self.prev_button.clicked.connect(self.on_prev)
        self.next_button.clicked.connect(self.on_next)
        self.finish_button.clicked.connect(self.accept)
        self._update_buttons()

    def _build_step_checks(self) -> None:
        widget = QWidget(self)
        layout = QVBoxLayout()
        ffmpeg_path = shutil.which("ffmpeg")
        playwright_info = "已安装" if shutil.which("playwright") else "未检测到"
        layout.addWidget(QLabel(f"FFmpeg: {'已检测' if ffmpeg_path else '未找到'}", widget))
        layout.addWidget(QLabel(f"Playwright: {playwright_info}", widget))
        widget.setLayout(layout)
        self.stack.addWidget(widget)

    def _build_step_database(self) -> None:
        widget = QWidget(self)
        form = QFormLayout()
        self.db_url_edit = QLineEdit(widget)
        if self.state.current_profile:
            self.db_url_edit.setText(self.state.current_profile.database.dsn)
        form.addRow("数据库 URL", self.db_url_edit)
        widget.setLayout(form)
        self.stack.addWidget(widget)

    def _build_step_storage(self) -> None:
        widget = QWidget(self)
        layout = QVBoxLayout()
        self.storage_path_edit = QLineEdit(widget)
        browse_button = QPushButton("选择 storage_state", widget)
        browse_button.clicked.connect(self.on_browse_storage)
        layout.addWidget(QLabel("选择 Playwright storage_state 文件", widget))
        layout.addWidget(self.storage_path_edit)
        layout.addWidget(browse_button)
        widget.setLayout(layout)
        self.stack.addWidget(widget)

    @Slot()
    def on_browse_storage(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择 storage_state", str(Path.cwd()))
        if path:
            self.storage_path_edit.setText(path)

    @Slot()
    def on_prev(self) -> None:
        index = max(0, self.stack.currentIndex() - 1)
        self.stack.setCurrentIndex(index)
        self._update_buttons()

    @Slot()
    def on_next(self) -> None:
        current = self.stack.currentIndex()
        index = min(self.stack.count() - 1, current + 1)
        if current == 1 and self.state.current_profile:
            profile = self.state.current_profile.model_copy()
            profile.database.dsn = self.db_url_edit.text().strip() or profile.database.dsn
            self.state.save_profile(profile)
        self.stack.setCurrentIndex(index)
        self._update_buttons()

    def accept(self) -> None:
        if self.state.current_profile:
            profile = self.state.current_profile.model_copy()
            profile.uploader.storage_state_path = (
                self.storage_path_edit.text().strip() or profile.uploader.storage_state_path
            )
            self.state.save_profile(profile)
        super().accept()

    def _update_buttons(self) -> None:
        self.prev_button.setEnabled(self.stack.currentIndex() > 0)
        is_last = self.stack.currentIndex() == self.stack.count() - 1
        self.next_button.setEnabled(not is_last)
        self.finish_button.setEnabled(is_last)


__all__ = ["FirstRunWizard"]
