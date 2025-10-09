"""上传配置表单。"""
from __future__ import annotations

from typing import Optional

import asyncio
from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QComboBox,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QHBoxLayout,
    QMessageBox,
)

from ...services.uploader_service import UploaderService
from ...state import AppState, UploaderSettings


class UploaderForm(QWidget):
    """上传设置表单。"""

    def __init__(self, state: AppState, uploader_service: UploaderService, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.state = state
        self.uploader_service = uploader_service

        self.platform_combo = QComboBox(self)
        self.platform_combo.addItems(["douyin", "xiaohongshu", "weixin_channels"])

        self.provider_combo = QComboBox(self)
        self.provider_combo.addItems(["web", "appium", "api", "none"])

        self.storage_edit = QLineEdit(self)
        self.appium_edit = QLineEdit(self)
        self.extra_edit = QTextEdit(self)

        self.save_button = QPushButton("保存", self)
        self.test_button = QPushButton("测试上传", self)

        layout = QFormLayout()
        layout.addRow("平台", self.platform_combo)
        layout.addRow("Provider", self.provider_combo)
        layout.addRow("storage_state 路径", self.storage_edit)
        layout.addRow("Appium Server", self.appium_edit)
        layout.addRow("额外参数(JSON)", self.extra_edit)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.test_button)
        layout.addRow(button_layout)
        self.setLayout(layout)

        self._load_from_state()
        self.save_button.clicked.connect(self.on_save)
        self.test_button.clicked.connect(self.on_test)

    def _load_from_state(self) -> None:
        profile = self.state.current_profile
        if not profile:
            return
        uploader = profile.uploader
        self.platform_combo.setCurrentText(uploader.platform)
        self.provider_combo.setCurrentText(uploader.provider)
        self.storage_edit.setText(uploader.storage_state_path or "")
        self.appium_edit.setText(uploader.appium_server or "")
        if uploader.extra:
            import json

            self.extra_edit.setText(json.dumps(uploader.extra, ensure_ascii=False, indent=2))
        else:
            self.extra_edit.clear()

    def refresh(self) -> None:
        """刷新表单。"""

        self._load_from_state()

    @Slot()
    def on_save(self) -> None:
        profile = self.state.current_profile
        if not profile:
            return
        extra_text = self.extra_edit.toPlainText().strip()
        extra_data = {}
        if extra_text:
            import json

            try:
                extra_data = json.loads(extra_text)
            except json.JSONDecodeError as exc:
                QMessageBox.warning(self, "JSON 错误", str(exc))
                return
        settings = UploaderSettings(
            platform=self.platform_combo.currentText(),
            provider=self.provider_combo.currentText(),
            storage_state_path=self.storage_edit.text().strip() or None,
            appium_server=self.appium_edit.text().strip() or None,
            extra=extra_data,
        )
        updated = profile.model_copy(update={"uploader": settings.model_dump()})
        self.state.save_profile(updated)
        QMessageBox.information(self, "成功", "上传配置已保存")

    @Slot()
    def on_test(self) -> None:
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(self.uploader_service.simulate_upload())
        finally:
            loop.close()
        QMessageBox.information(
            self,
            "测试结果",
            f"{result.message}\nPayload: {result.payload}",
        )


__all__ = ["UploaderForm"]
