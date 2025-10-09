"""历史记录视图。"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
)

from ...services import db_service
from ...state import AppState


class RunsView(QWidget):
    """显示历史运行与上传记录。"""

    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.state = state

        self.refresh_button = QPushButton("刷新", self)
        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "时间", "类型", "状态", "详情"])
        self.table.horizontalHeader().setStretchLastSection(True)

        layout = QVBoxLayout()
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.refresh_button)
        layout.addLayout(control_layout)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.refresh_button.clicked.connect(self.refresh)
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)

    @Slot()
    def refresh(self) -> None:
        profile = self.state.current_profile
        if not profile:
            return
        try:
            engine = db_service.build_engine(profile.database)
            runs = db_service.fetch_recent_runs(engine)
            uploads = db_service.fetch_recent_uploads(engine)
        except db_service.DatabaseError as exc:
            QMessageBox.warning(self, "数据库", str(exc))
            return
        records: List[tuple[str, str, str, str, str]] = []
        for row in runs:
            records.append(
                (
                    str(row.get("id")),
                    str(row.get("created_at")),
                    "run",
                    str(row.get("status")),
                    str(row.get("output_path")),
                )
            )
        for row in uploads:
            records.append(
                (
                    str(row.get("id")),
                    str(row.get("created_at")),
                    "upload",
                    str(row.get("status")),
                    str(row.get("response_payload")),
                )
            )
        records.sort(key=lambda item: item[1], reverse=True)
        self.table.setRowCount(len(records))
        for index, record in enumerate(records):
            for col, value in enumerate(record):
                self.table.setItem(index, col, QTableWidgetItem(value))

    @Slot(int, int)
    def on_cell_double_clicked(self, row: int, column: int) -> None:
        item = self.table.item(row, column)
        if not item:
            return
        detail = self.table.item(row, 4)
        QMessageBox.information(
            self,
            "详情",
            detail.text() if detail else "无详情",
        )


__all__ = ["RunsView"]
