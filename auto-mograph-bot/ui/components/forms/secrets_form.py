"""密钥管理界面，提供加密存储与登录态维护功能。"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...services.secrets_service import SecretsError, SecretsLockedError, SecretsService
from ...state import AppState


class SecretsForm(QWidget):
    """提供主密码设置、后端切换以及登录态导入/管理。"""

    DEFAULT_NAMES = ["douyin_state", "xiaohongshu_state", "weixin_channels_state"]

    def __init__(
        self, state: AppState, secrets_service: SecretsService, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.state = state
        self.secrets_service = secrets_service

        self.backend_status = QLabel(self)
        self.fernet_radio = QRadioButton("Fernet 本地加密", self)
        self.keyring_radio = QRadioButton("系统 Keyring", self)
        self.fernet_radio.setChecked(self.secrets_service.backend == "fernet")
        self.keyring_radio.setChecked(self.secrets_service.backend == "keyring")

        self.password_field = QLineEdit(self)
        self.password_field.setEchoMode(QLineEdit.Password)
        self.password_confirm_field = QLineEdit(self)
        self.password_confirm_field.setEchoMode(QLineEdit.Password)

        self.set_password_button = QPushButton("设置主密码", self)
        self.import_button = QPushButton("导入登录态", self)
        self.delete_button = QPushButton("删除所选", self)
        self.refresh_button = QPushButton("刷新状态", self)

        self.secret_name_field = QLineEdit(self)
        self.secret_name_field.setPlaceholderText("例如：douyin_state")
        if self.DEFAULT_NAMES:
            self.secret_name_field.setText(self.DEFAULT_NAMES[0])
        self.ttl_field = QSpinBox(self)
        self.ttl_field.setRange(1, 365)
        self.ttl_field.setValue(30)

        self.table = QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(["名称", "创建时间", "剩余天数", "状态"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(self.table.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)

        backend_layout = QHBoxLayout()
        backend_layout.addWidget(self.fernet_radio)
        backend_layout.addWidget(self.keyring_radio)

        form = QFormLayout()
        form.addRow("存储后端", backend_layout)
        form.addRow("主密码", self.password_field)
        form.addRow("确认主密码", self.password_confirm_field)
        form.addRow(self.set_password_button)
        form.addRow("登录态名称", self.secret_name_field)
        form.addRow("有效期 (天)", self.ttl_field)

        actions = QHBoxLayout()
        actions.addWidget(self.import_button)
        actions.addWidget(self.delete_button)
        actions.addWidget(self.refresh_button)
        form.addRow(actions)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(QLabel("已保存的登录态", self))
        layout.addWidget(self.table)
        layout.addWidget(self.backend_status)
        self.setLayout(layout)

        self.fernet_radio.toggled.connect(self.on_backend_changed)
        self.keyring_radio.toggled.connect(self.on_backend_changed)
        self.set_password_button.clicked.connect(self.on_set_master_password)
        self.import_button.clicked.connect(self.on_import_secret)
        self.delete_button.clicked.connect(self.on_delete_secret)
        self.refresh_button.clicked.connect(self.refresh_table)

        self.refresh_table()

    # ------------------------------------------------------------------
    @Slot()
    def on_backend_changed(self) -> None:
        backend = "keyring" if self.keyring_radio.isChecked() else "fernet"
        if backend == self.secrets_service.backend:
            self._update_backend_status()
            return
        try:
            self.secrets_service.use_backend(backend)
        except SecretsError as exc:
            QMessageBox.critical(self, "切换失败", str(exc))
            return
        self.password_field.clear()
        self.password_confirm_field.clear()
        QMessageBox.information(self, "提示", "后端已切换，请重新设置主密码。")
        self.refresh_table()

    # ------------------------------------------------------------------
    @Slot()
    def on_set_master_password(self) -> None:
        password = self.password_field.text().strip()
        confirm = self.password_confirm_field.text().strip()
        if not password or password != confirm:
            QMessageBox.warning(self, "提示", "请填写并确认主密码")
            return
        try:
            self.secrets_service.set_master_password(password)
        except SecretsError as exc:
            QMessageBox.critical(self, "失败", str(exc))
            return
        QMessageBox.information(self, "成功", "主密码已设置，密钥库已解锁。")
        self.refresh_table()

    # ------------------------------------------------------------------
    @Slot()
    def on_import_secret(self) -> None:
        name = self.secret_name_field.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请填写登录态名称")
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 storage_state JSON", str(Path.home()), "JSON 文件 (*.json);;所有文件 (*)"
        )
        if not file_path:
            return
        path = Path(file_path)
        try:
            payload = path.read_text(encoding="utf-8")
            self.secrets_service.store(name, payload.encode("utf-8"), ttl_days=self.ttl_field.value())
        except (OSError, UnicodeDecodeError) as exc:
            QMessageBox.critical(self, "读取失败", str(exc))
            return
        except SecretsLockedError as exc:
            QMessageBox.warning(self, "提示", str(exc))
            return
        except SecretsError as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        try:
            path.unlink()
        except OSError:
            pass
        QMessageBox.information(self, "成功", "登录态已导入并加密保存。")
        self.refresh_table()

    # ------------------------------------------------------------------
    @Slot()
    def on_delete_secret(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请选择要删除的登录态")
            return
        name_item = self.table.item(row, 0)
        if not name_item:
            return
        name = name_item.text()
        confirm = QMessageBox.question(self, "确认删除", f"确定删除 {name} 吗？")
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self.secrets_service.delete(name)
        except SecretsError as exc:
            QMessageBox.critical(self, "删除失败", str(exc))
            return
        QMessageBox.information(self, "成功", "登录态已删除。")
        self.refresh_table()

    # ------------------------------------------------------------------
    @Slot()
    def refresh_table(self) -> None:
        try:
            entries = self.secrets_service.list_all()
        except SecretsError as exc:
            self.table.setRowCount(0)
            self.backend_status.setText(f"状态：{exc}")
            return
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            name_item = QTableWidgetItem(str(entry["name"]))
            name_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            created_item = QTableWidgetItem(str(entry["created_at"]))
            created_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            days_left = int(entry["days_left"])
            days_item = QTableWidgetItem(f"{days_left}")
            days_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            status_text = "已过期" if entry["is_expired"] else "有效"
            status_item = QTableWidgetItem(status_text)
            status_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, created_item)
            self.table.setItem(row, 2, days_item)
            self.table.setItem(row, 3, status_item)
        self._update_backend_status(len(entries))

    # ------------------------------------------------------------------
    def _update_backend_status(self, count: Optional[int] = None) -> None:
        backend = "Fernet 本地加密" if self.secrets_service.backend == "fernet" else "系统 Keyring"
        if count is None:
            try:
                count = len(self.secrets_service.list_all())
            except SecretsError:
                count = 0
        self.backend_status.setText(f"当前后端：{backend}｜条目数量：{count}")


__all__ = ["SecretsForm"]
