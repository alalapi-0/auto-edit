"""YAML 配置编辑器视图。"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QPlainTextEdit,
    QMessageBox,
    QFileDialog,
)

from src.config import get_config_center

from ...state import AppState
from ...utils import yaml_io


class ConfigEditorView(QWidget):
    """用于浏览与编辑 YAML 配置，同时支持 Profile 导入导出。"""

    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.state = state
        self.center = get_config_center()
        self.combo = QComboBox(self)
        self.editor = QPlainTextEdit(self)
        self.save_button = QPushButton("保存", self)
        self.reload_button = QPushButton("重新加载", self)
        self.validate_button = QPushButton("校验", self)
        self.export_button = QPushButton("导出 Profile", self)
        self.import_button = QPushButton("导入 Profile", self)

        control_layout = QHBoxLayout()
        control_layout.addWidget(self.combo)
        control_layout.addWidget(self.reload_button)
        control_layout.addWidget(self.save_button)
        control_layout.addWidget(self.validate_button)
        control_layout.addWidget(self.export_button)
        control_layout.addWidget(self.import_button)

        layout = QVBoxLayout()
        layout.addLayout(control_layout)
        layout.addWidget(self.editor)
        self.setLayout(layout)

        try:
            self.center.reload()
        except Exception:
            # 即使加载失败也允许手工编辑，后续操作会提示错误。
            pass
        self._populate_files()
        self.combo.currentTextChanged.connect(self.load_selected)
        self.reload_button.clicked.connect(self.on_reload)
        self.save_button.clicked.connect(self.on_save)
        self.validate_button.clicked.connect(self.on_validate)
        self.export_button.clicked.connect(self.on_export_profile)
        self.import_button.clicked.connect(self.on_import_profile)
        if self.combo.count() > 0:
            self.load_selected(self.combo.currentText())

    def _populate_files(self) -> None:
        self.combo.clear()
        for path in sorted(self.state.config_dir.glob("*.yaml")):
            self.combo.addItem(str(path))

    def refresh(self) -> None:
        """刷新文件列表并重新加载当前文件。"""

        try:
            self.center.reload()
        except Exception:
            pass
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
            data = yaml.safe_load(self.editor.toPlainText() or "") or {}
            if not isinstance(data, dict):
                raise ValueError("配置文件必须是映射结构")
            self.center.validate(data)
            with open(path, "w", encoding="utf-8") as handle:
                yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=False)
            self.center.reload()
        except OSError as exc:
            QMessageBox.critical(self, "写入失败", str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - 直接反馈错误
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        QMessageBox.information(self, "成功", "配置已保存")

    @Slot()
    def on_validate(self) -> None:
        path = self.combo.currentText()
        if not path:
            return
        try:
            content = yaml_io.load_yaml_file(path)
            self.center.validate(content)
        except Exception as exc:  # noqa: BLE001 - 直接反馈错误
            QMessageBox.warning(self, "校验失败", str(exc))
            return
        QMessageBox.information(self, "校验", "文件结构有效")

    @Slot()
    def on_export_profile(self) -> None:
        default_name = self.state.current_profile.name if self.state.current_profile else "profile"
        default_path = self.center.profile_directory / f"{default_name}.yaml"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 Profile",
            str(default_path),
            "YAML Files (*.yaml)",
        )
        if not path:
            return
        name = Path(path).stem
        try:
            self.center.export_profile(name, path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "导出失败", str(exc))
            return
        QMessageBox.information(self, "导出", f"Profile 已保存到 {path}")

    @Slot()
    def on_import_profile(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "导入 Profile",
            str(self.center.profile_directory),
            "YAML Files (*.yaml)",
        )
        if not path:
            return
        try:
            target = self.center.import_profile(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "导入失败", str(exc))
            return
        QMessageBox.information(self, "导入", f"Profile 已同步到 {target}")
        self.refresh()


__all__ = ["ConfigEditorView"]
