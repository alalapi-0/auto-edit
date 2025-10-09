"""VPS Provider 表单。"""
from __future__ import annotations

import asyncio
import json
from typing import Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QComboBox,
    QTextEdit,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
)

from ...services.vps_service import get_providers
from ...state import AppState, VPSSettings


class VPSForm(QWidget):
    """管理 VPS Provider 的 UI。"""

    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.state = state
        self.providers = get_providers()
        self.current_instance_id: Optional[str] = None

        self.provider_combo = QComboBox(self)
        self.provider_combo.addItems(self.providers.keys())

        self.info_label = QLabel("选择 Provider 以查看说明", self)
        self.options_edit = QTextEdit(self)
        self.options_edit.setPlaceholderText('{"api_key": "", "region": "auto"}')

        self.create_button = QPushButton("创建 VPS", self)
        self.destroy_button = QPushButton("销毁", self)
        self.save_button = QPushButton("保存", self)

        layout = QFormLayout()
        layout.addRow("Provider", self.provider_combo)
        layout.addRow("说明", self.info_label)
        layout.addRow("参数(JSON)", self.options_edit)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.create_button)
        button_layout.addWidget(self.destroy_button)
        layout.addRow(button_layout)
        self.setLayout(layout)

        self._load_from_state()

        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        self.save_button.clicked.connect(self.on_save)
        self.create_button.clicked.connect(self.on_create)
        self.destroy_button.clicked.connect(self.on_destroy)

    def _load_from_state(self) -> None:
        profile = self.state.current_profile
        if not profile:
            return
        settings = profile.vps
        self.provider_combo.setCurrentText(settings.provider)
        if settings.options:
            self.options_edit.setText(json.dumps(settings.options, ensure_ascii=False, indent=2))
        else:
            self.options_edit.clear()
        self.on_provider_changed(settings.provider)

    def refresh(self) -> None:
        """刷新表单。"""

        self._load_from_state()

    @Slot(str)
    def on_provider_changed(self, name: str) -> None:
        if name == "local":
            self.info_label.setText("本地 Provider：直接使用当前机器执行任务，不创建云资源。")
            self.options_edit.setPlainText("{}")
        elif name == "placeholder":
            self.info_label.setText("占位 Provider：模拟云厂商流程，输入伪 API Key 即可演示。")
        else:
            self.info_label.setText("请在 JSON 中填写 Provider 所需的参数。")

    @Slot()
    def on_save(self) -> None:
        profile = self.state.current_profile
        if not profile:
            return
        options_text = self.options_edit.toPlainText().strip()
        options = {}
        if options_text:
            try:
                options = json.loads(options_text)
            except json.JSONDecodeError as exc:
                QMessageBox.warning(self, "JSON 错误", str(exc))
                return
        settings = VPSSettings(provider=self.provider_combo.currentText(), options=options)
        updated = profile.model_copy(update={"vps": settings.model_dump()})
        self.state.save_profile(updated)
        QMessageBox.information(self, "成功", "VPS 配置已保存")

    @Slot()
    def on_create(self) -> None:
        provider = self.providers.get(self.provider_combo.currentText())
        if not provider:
            return
        options_text = self.options_edit.toPlainText().strip()
        options = {}
        if options_text:
            try:
                options = json.loads(options_text)
            except json.JSONDecodeError as exc:
                QMessageBox.warning(self, "JSON 错误", str(exc))
                return
        loop = asyncio.new_event_loop()
        try:
            instance = loop.run_until_complete(provider.create(options))
        finally:
            loop.close()
        self.current_instance_id = instance.identifier
        QMessageBox.information(
            self,
            "创建成功",
            f"ID: {instance.identifier}\n状态: {instance.status}\n附加: {instance.metadata}",
        )

    @Slot()
    def on_destroy(self) -> None:
        provider = self.providers.get(self.provider_combo.currentText())
        if not provider:
            return
        if not self.current_instance_id:
            QMessageBox.information(self, "提示", "当前没有可销毁的实例")
            return
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(provider.destroy(self.current_instance_id))
        finally:
            loop.close()
        QMessageBox.information(self, "已销毁", f"实例 {self.current_instance_id} 已释放")
        self.current_instance_id = None


__all__ = ["VPSForm"]
