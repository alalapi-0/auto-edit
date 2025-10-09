"""YAML 配置编辑器视图。"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QPlainTextEdit,
    QMessageBox,
)

from ...state import AppState
from ...utils import yaml_io


class ConfigEditorView(QWidget):
    """用于浏览与编辑 YAML 配置。"""

    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.state = state
        self.combo = QComboBox(self)
        self.editor = QPlainTextEdit(self)
        self.save_button = QPushButton("保存", self)
        self.reload_button = QPushButton("重新加载", self)
        self.validate_button = QPushButton("校验", self)

        control_layout = QHBoxLayout()
        control_layout.addWidget(self.combo)
        control_layout.addWidget(self.reload_button)
        control_layout.addWidget(self.save_button)
        control_layout.addWidget(self.validate_button)

        layout = QVBoxLayout()
        layout.addLayout(control_layout)
        layout.addWidget(self.editor)
        self.setLayout(layout)

        self._populate_files()
        self.combo.currentTextChanged.connect(self.load_selected)
        self.reload_button.clicked.connect(self.on_reload)
        self.save_button.clicked.connect(self.on_save)
        self.validate_button.clicked.connect(self.on_validate)
        if self.combo.count() > 0:
            self.load_selected(self.combo.currentText())

    def _populate_files(self) -> None:
        self.combo.clear()
        for path in sorted(self.state.config_dir.glob("*.yaml")):
            self.combo.addItem(str(path))

    def refresh(self) -> None:
        """刷新文件列表并重新加载当前文件。"""

        current = self.combo.currentText()
        self._populate_files()
        if current:
            index = self.combo.findText(current)
            if index != -1:
                self.combo.setCurrentIndex(index)
            else:
                self.load_selected(self.combo.currentText())

    @Slot(str)
    def load_selected(self, path: str) -> None:
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                self.editor.setPlainText(handle.read())
        except OSError as exc:
            QMessageBox.warning(self, "读取失败", str(exc))

    @Slot()
    def on_reload(self) -> None:
        self.load_selected(self.combo.currentText())

    @Slot()
    def on_save(self) -> None:
        path = self.combo.currentText()
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(self.editor.toPlainText())
        except OSError as exc:
            QMessageBox.critical(self, "写入失败", str(exc))
            return
        QMessageBox.information(self, "成功", "配置已保存")

    @Slot()
    def on_validate(self) -> None:
        path = self.combo.currentText()
        if not path:
            return
        try:
            content = yaml_io.load_yaml_file(path)
            if not self.state.current_profile:
                raise ValueError("当前没有激活的 Profile")
            yaml_io.validate_yaml_with_model(content, type(self.state.current_profile))
        except Exception as exc:  # noqa: BLE001 - 直接反馈错误
            QMessageBox.warning(self, "校验失败", str(exc))
            return
        QMessageBox.information(self, "校验", "文件结构有效")


__all__ = ["ConfigEditorView"]
