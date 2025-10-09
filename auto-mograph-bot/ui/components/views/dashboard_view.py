"""Dashboard 视图。"""
from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QGridLayout,
    QMessageBox,
)

from ...services import db_service
from ...services.pipeline_service import PipelineService
from ...services.uploader_service import UploaderService
from ...state import AppState


class DashboardView(QWidget):
    """显示概览与快捷操作。"""

    def __init__(
        self,
        state: AppState,
        pipeline_service: PipelineService,
        uploader_service: UploaderService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.state = state
        self.pipeline_service = pipeline_service
        self.uploader_service = uploader_service
        self.log_sink: Optional[Callable[[str], None]] = None

        self.db_status = QLabel("DB: 未测试", self)
        self.disk_status = QLabel("磁盘: 未检测", self)
        self.ffmpeg_status = QLabel("FFmpeg: 未检测", self)
        self.playwright_status = QLabel("Playwright: 未检测", self)

        self.refresh_button = QPushButton("刷新状态", self)
        self.test_db_button = QPushButton("测试数据库", self)
        self.test_ffmpeg_button = QPushButton("测试 FFmpeg", self)
        self.test_playwright_button = QPushButton("测试登录态", self)
        self.run_button = QPushButton("开始生成", self)
        self.upload_button = QPushButton("模拟上传", self)

        layout = QVBoxLayout()
        grid = QGridLayout()
        grid.addWidget(self.db_status, 0, 0)
        grid.addWidget(self.disk_status, 1, 0)
        grid.addWidget(self.ffmpeg_status, 2, 0)
        grid.addWidget(self.playwright_status, 3, 0)
        layout.addLayout(grid)

        button_layout = QGridLayout()
        button_layout.addWidget(self.refresh_button, 0, 0)
        button_layout.addWidget(self.test_db_button, 0, 1)
        button_layout.addWidget(self.test_ffmpeg_button, 1, 0)
        button_layout.addWidget(self.test_playwright_button, 1, 1)
        button_layout.addWidget(self.run_button, 2, 0)
        button_layout.addWidget(self.upload_button, 2, 1)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        self.refresh_button.clicked.connect(self.refresh_status)
        self.test_db_button.clicked.connect(self.on_test_db)
        self.test_ffmpeg_button.clicked.connect(self.on_test_ffmpeg)
        self.test_playwright_button.clicked.connect(self.on_test_playwright)
        self.run_button.clicked.connect(self.on_run_pipeline)
        self.upload_button.clicked.connect(self.on_simulate_upload)

        self.refresh_status()

    # ------------------------------------------------------------------
    @Slot()
    def refresh_status(self) -> None:
        self._update_disk_status()
        self.db_status.setText("DB: 未测试")
        self.ffmpeg_status.setText("FFmpeg: 未检测")
        self.playwright_status.setText("Playwright: 未检测")

    def _update_disk_status(self) -> None:
        usage = shutil.disk_usage(Path.cwd())
        free_gb = usage.free / (1024 ** 3)
        self.disk_status.setText(f"磁盘: {free_gb:.1f} GB 可用")

    # ------------------------------------------------------------------
    @Slot()
    def on_test_db(self) -> None:
        profile = self.state.current_profile
        if not profile:
            return
        try:
            db_service.test_connection(profile.database)
        except db_service.DatabaseError as exc:
            self.db_status.setText(f"DB: 失败 - {exc}")
            QMessageBox.warning(self, "数据库", str(exc))
            return
        self.db_status.setText("DB: 连接正常")

    @Slot()
    def on_test_ffmpeg(self) -> None:
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            self.ffmpeg_status.setText("FFmpeg: 未找到")
            QMessageBox.warning(self, "FFmpeg", "未找到 ffmpeg 可执行文件")
            return
        try:
            subprocess.run([ffmpeg_path, "-version"], check=True, capture_output=True)
        except subprocess.CalledProcessError as exc:
            self.ffmpeg_status.setText("FFmpeg: 失败")
            QMessageBox.warning(self, "FFmpeg", exc.stderr.decode("utf-8", errors="ignore"))
            return
        self.ffmpeg_status.setText(f"FFmpeg: {ffmpeg_path}")

    @Slot()
    def on_test_playwright(self) -> None:
        profile = self.state.current_profile
        if not profile:
            return
        path = profile.uploader.storage_state_path
        if not path:
            self.playwright_status.setText("Playwright: 未配置 storage_state")
            return
        storage_path = Path(path)
        if storage_path.exists():
            self.playwright_status.setText(f"Playwright: {storage_path}")
        else:
            self.playwright_status.setText("Playwright: 文件不存在")

    @Slot()
    def on_run_pipeline(self) -> None:
        loop = asyncio.new_event_loop()
        try:
            exit_code = loop.run_until_complete(self.pipeline_service.run_mvp(log=self._append_log))
        finally:
            loop.close()
        QMessageBox.information(self, "流水线", f"任务结束，退出码 {exit_code}")

    def _append_log(self, line: str) -> None:
        if self.log_sink:
            self.log_sink(line)
        else:
            print(line)

    def set_log_sink(self, sink: Callable[[str], None]) -> None:
        """设置日志输出位置。"""

        self.log_sink = sink

    @Slot()
    def on_simulate_upload(self) -> None:
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(self.uploader_service.simulate_upload())
        finally:
            loop.close()
        QMessageBox.information(self, "上传", result.message)


__all__ = ["DashboardView"]
