"""数据库配置表单。"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QComboBox,
    QLineEdit,
    QPushButton,
    QLabel,
    QHBoxLayout,
    QMessageBox,
)

from ...services import db_service
from ...state import AppState, DatabaseSettings


class DatabaseForm(QWidget):
    """数据库连接配置表单组件。"""

    status_changed = Signal(str)

    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.state = state

        self.backend_combo = QComboBox(self)
        self.backend_combo.addItems(["sqlite", "mysql", "postgres"])

        self.dsn_edit = QLineEdit(self)
        self.status_label = QLabel("未测试", self)

        self.test_button = QPushButton("测试连接", self)
        self.init_button = QPushButton("初始化表", self)
        self.save_button = QPushButton("保存", self)

        form_layout = QFormLayout()
        form_layout.addRow("数据库类型", self.backend_combo)
        form_layout.addRow("连接字符串", self.dsn_edit)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.test_button)
        button_layout.addWidget(self.init_button)
        button_layout.addWidget(self.save_button)
        form_layout.addRow(button_layout)
        form_layout.addRow("状态", self.status_label)

        self.setLayout(form_layout)
        self._load_from_state()

        self.test_button.clicked.connect(self.on_test_connection)
        self.save_button.clicked.connect(self.on_save)
        self.init_button.clicked.connect(self.on_initialize)

    # ------------------------------------------------------------------
    def _load_from_state(self) -> None:
        profile = self.state.current_profile
        if not profile:
            return
        self.backend_combo.setCurrentText(profile.database.backend)
        self.dsn_edit.setText(profile.database.dsn)

    def refresh(self) -> None:
        """外部调用以刷新表单内容。"""

        self._load_from_state()

    # ------------------------------------------------------------------
    @Slot()
    def on_save(self) -> None:
        backend = self.backend_combo.currentText()
        dsn = self.dsn_edit.text().strip()
        if not dsn:
            QMessageBox.warning(self, "提示", "请填写连接字符串")
            return
        profile = self.state.current_profile
        if not profile:
            return
        updated = profile.model_copy(update={"database": {"backend": backend, "dsn": dsn}})
        self.state.save_profile(updated)
        self.status_label.setText("已保存")
        self.status_changed.emit("saved")

    @Slot()
    def on_test_connection(self) -> None:
        backend = self.backend_combo.currentText()
        dsn = self.dsn_edit.text().strip()
        settings = DatabaseSettings(backend=backend, dsn=dsn)
        try:
            db_service.test_connection(settings)
        except db_service.DatabaseError as exc:
            self.status_label.setText(f"失败: {exc}")
            self.status_changed.emit("failed")
            return
        self.status_label.setText("连接成功")
        self.status_changed.emit("ok")

    @Slot()
    def on_initialize(self) -> None:
        backend = self.backend_combo.currentText()
        dsn = self.dsn_edit.text().strip()
        engine = db_service.build_engine(DatabaseSettings(backend=backend, dsn=dsn))
        statements = [
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                prompt TEXT,
                status TEXT,
                output_path TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                platform TEXT,
                status TEXT,
                response_payload TEXT
            )
            """,
        ]
        try:
            db_service.initialize_schema(engine, statements)
        except db_service.DatabaseError as exc:
            QMessageBox.critical(self, "初始化失败", str(exc))
            return
        QMessageBox.information(self, "成功", "表结构已初始化")


__all__ = ["DatabaseForm"]
