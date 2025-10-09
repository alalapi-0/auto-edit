"""实时日志视图。"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QFileDialog,
)

from ...state import AppState


class LogsView(QWidget):
    """显示流水线输出日志。"""

    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.state = state

        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("搜索关键字")
        self.export_button = QPushButton("导出", self)
        self.clear_button = QPushButton("清空", self)

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)

        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(self.export_button)
        search_layout.addWidget(self.clear_button)

        layout = QVBoxLayout()
        layout.addLayout(search_layout)
        layout.addWidget(self.text_edit)
        self.setLayout(layout)

        self.search_edit.textChanged.connect(self.on_search)
        self.export_button.clicked.connect(self.on_export)
        self.clear_button.clicked.connect(self.on_clear)

    def append_log(self, line: str) -> None:
        self.text_edit.append(line)

    @Slot(str)
    def on_search(self, term: str) -> None:
        cursor = self.text_edit.textCursor()
        document = self.text_edit.document()
        cursor.setPosition(0)
        self.text_edit.setTextCursor(cursor)
        if term:
            found = document.find(term, cursor)
            if not found.isNull():
                self.text_edit.setTextCursor(found)

    @Slot()
    def on_export(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(self, "导出日志", "logs.txt")
        if not file_path:
            return
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(self.text_edit.toPlainText())

    @Slot()
    def on_clear(self) -> None:
        self.text_edit.clear()


__all__ = ["LogsView"]
