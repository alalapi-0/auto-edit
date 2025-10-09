"""密钥管理表单。"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QLineEdit,
    QRadioButton,
    QButtonGroup,
    QPushButton,
    QLabel,
    QHBoxLayout,
    QMessageBox,
)

from ...services.secrets_service import (
    KeyringBackend,
    LocalEncryptedBackend,
    SecretStorageError,
    SecretsService,
)
from ...state import AppState


class SecretsForm(QWidget):
    """管理账号与密钥。"""

    def __init__(self, state: AppState, secrets_service: SecretsService, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.state = state
        self.secrets_service = secrets_service
        self.local_backend = LocalEncryptedBackend()
        self.keyring_backend = KeyringBackend(service_name="auto-mograph-bot")

        self.key_field = QLineEdit(self)
        self.value_field = QLineEdit(self)
        self.value_field.setEchoMode(QLineEdit.Password)
        self.service_field = QLineEdit(self)

        self.password_field = QLineEdit(self)
        self.password_field.setEchoMode(QLineEdit.Password)
        self.password_confirm_field = QLineEdit(self)
        self.password_confirm_field.setEchoMode(QLineEdit.Password)

        self.keyring_radio = QRadioButton("系统 Keyring", self)
        self.local_radio = QRadioButton("本地加密文件", self)
        self.keyring_radio.setChecked(True)
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.keyring_radio)
        self.mode_group.addButton(self.local_radio)

        self.save_button = QPushButton("保存密钥", self)
        self.read_button = QPushButton("读取", self)
        self.update_backend_button = QPushButton("应用后端", self)
        self.status_label = QLabel("后端: keyring", self)

        form = QFormLayout()
        backend_layout = QHBoxLayout()
        backend_layout.addWidget(self.keyring_radio)
        backend_layout.addWidget(self.local_radio)
        form.addRow("存储后端", backend_layout)
        form.addRow("服务名", self.service_field)
        form.addRow("Key", self.key_field)
        form.addRow("Value", self.value_field)
        form.addRow("主密码", self.password_field)
        form.addRow("确认密码", self.password_confirm_field)
        form.addRow(self.update_backend_button)
        form.addRow(self.save_button)
        form.addRow(self.read_button)
        form.addRow("状态", self.status_label)
        self.setLayout(form)

        self.service_field.setText(self.keyring_backend.service_name)

        self.update_backend_button.clicked.connect(self.on_apply_backend)
        self.save_button.clicked.connect(self.on_save_secret)
        self.read_button.clicked.connect(self.on_read_secret)
        self.mode_group.buttonClicked.connect(self.on_mode_changed)
        self.on_mode_changed()

    @Slot()
    def on_mode_changed(self) -> None:
        is_keyring = self.keyring_radio.isChecked()
        self.password_field.setEnabled(not is_keyring)
        self.password_confirm_field.setEnabled(not is_keyring)
        self.status_label.setText(f"后端: {'keyring' if is_keyring else 'local_encrypted'}")

    @Slot()
    def on_apply_backend(self) -> None:
        if self.keyring_radio.isChecked():
            service_name = self.service_field.text().strip() or "auto-mograph-bot"
            self.keyring_backend.service_name = service_name
            self.secrets_service.replace_backend(self.keyring_backend)
            QMessageBox.information(self, "成功", "已切换到系统 keyring")
        else:
            password = self.password_field.text().strip()
            confirm = self.password_confirm_field.text().strip()
            if not password or password != confirm:
                QMessageBox.warning(self, "提示", "请填写并确认主密码")
                return
            try:
                self.local_backend.set_master_password(password)
            except SecretStorageError as exc:
                QMessageBox.critical(self, "失败", str(exc))
                return
            self.secrets_service.replace_backend(self.local_backend)
            QMessageBox.information(self, "成功", "已切换到本地加密文件")

    @Slot()
    def on_save_secret(self) -> None:
        key = self.key_field.text().strip()
        value = self.value_field.text().strip()
        if not key or not value:
            QMessageBox.warning(self, "提示", "请填写 Key 和 Value")
            return
        try:
            self.secrets_service.set_secret(key, value)
        except SecretStorageError as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        QMessageBox.information(self, "成功", "密钥已保存")

    @Slot()
    def on_read_secret(self) -> None:
        key = self.key_field.text().strip()
        if not key:
            QMessageBox.warning(self, "提示", "请填写 Key")
            return
        try:
            value = self.secrets_service.get_secret(key)
        except SecretStorageError as exc:
            QMessageBox.critical(self, "读取失败", str(exc))
            return
        if value is None:
            QMessageBox.information(self, "提示", "未找到对应密钥")
        else:
            QMessageBox.information(self, "密钥", value)


__all__ = ["SecretsForm"]
