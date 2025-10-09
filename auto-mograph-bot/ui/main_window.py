"""PySide6 主窗口实现。"""
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QWidget,
    QVBoxLayout,
    QLabel,
    QComboBox,
)

from .components.forms.db_form import DatabaseForm
from .components.forms.pipeline_form import PipelineForm
from .components.forms.uploader_form import UploaderForm
from .components.forms.vps_form import VPSForm
from .components.forms.secrets_form import SecretsForm
from .components.views.dashboard_view import DashboardView
from .components.views.logs_view import LogsView
from .components.views.runs_view import RunsView
from .components.views.config_editor import ConfigEditorView
from .components.views.first_run_wizard import FirstRunWizard
from .services.pipeline_service import PipelineService
from .services.secrets_service import SecretsService
from .services.uploader_service import UploaderService
from .state import AppState


class MainWindow(QMainWindow):
    """应用主窗口。"""

    def __init__(self, state: AppState, *, show_wizard: bool = True) -> None:
        super().__init__()
        self.state = state
        self._show_wizard = show_wizard
        self.setWindowTitle("Auto Mograph 控制台")
        self.resize(1200, 768)

        self.pipeline_service = PipelineService(state)
        self.uploader_service = UploaderService(state)
        self.secrets_service = SecretsService()

        self.dashboard_view = DashboardView(state, self.pipeline_service, self.uploader_service)
        self.pipeline_form = PipelineForm(state)
        self.uploader_form = UploaderForm(state, self.uploader_service)
        self.db_form = DatabaseForm(state)
        self.vps_form = VPSForm(state)
        self.secrets_form = SecretsForm(state, self.secrets_service)
        self.config_editor = ConfigEditorView(state)
        self.logs_view = LogsView(state)
        self.runs_view = RunsView(state)
        self.dashboard_view.set_log_sink(self.logs_view.append_log)

        self.views_order = [
            ("总览", self.dashboard_view),
            ("生成参数", self.pipeline_form),
            ("上传配置", self.uploader_form),
            ("数据库", self.db_form),
            ("VPS", self.vps_form),
            ("密钥", self.secrets_form),
            ("配置文件", self.config_editor),
            ("运行日志", self.logs_view),
            ("历史记录", self.runs_view),
        ]

        self.profile_combo = QComboBox(self)
        self.profile_combo.addItems(self.state.list_profiles())
        self.profile_combo.setCurrentText(self.state.current_profile.name if self.state.current_profile else "")
        self.profile_add_button = QPushButton("新建 Profile", self)
        self.profile_save_button = QPushButton("另存为", self)

        profile_bar = QHBoxLayout()
        profile_bar.addWidget(QLabel("Profile", self))
        profile_bar.addWidget(self.profile_combo)
        profile_bar.addWidget(self.profile_add_button)
        profile_bar.addWidget(self.profile_save_button)
        profile_bar.addStretch()

        self.nav_list = QListWidget(self)
        self.stack = QStackedWidget(self)
        for label, widget in self.views_order:
            QListWidgetItem(label, self.nav_list)
            self.stack.addWidget(widget)

        splitter = QSplitter(self)
        splitter.addWidget(self.nav_list)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.nav_list.setMaximumWidth(200)

        central_widget = QWidget(self)
        main_layout = QVBoxLayout()
        main_layout.addLayout(profile_bar)
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.profile_combo.currentTextChanged.connect(self.on_profile_changed)
        self.profile_add_button.clicked.connect(self.on_profile_add)
        self.profile_save_button.clicked.connect(self.on_profile_save_as)
        self.nav_list.setCurrentRow(0)

        self.refresh_views()
        if self._show_wizard:
            self._maybe_show_wizard()
        self._init_status_timer()

    # ------------------------------------------------------------------
    def _maybe_show_wizard(self) -> None:
        flag = Path("profiles/.first_run_done")
        if not flag.exists():
            wizard = FirstRunWizard(self.state, self)
            result = wizard.exec()
            if result:
                flag.touch()
                self.refresh_views()

    # ------------------------------------------------------------------
    def refresh_views(self) -> None:
        """刷新所有依赖配置的视图。"""

        self.pipeline_form.refresh()
        self.uploader_form.refresh()
        self.db_form.refresh()
        self.vps_form.refresh()
        self.config_editor.refresh()
        self.runs_view.refresh()
        self.dashboard_view.refresh_status()
        self.refresh_status_bar()

    # ------------------------------------------------------------------
    def on_profile_changed(self, name: str) -> None:
        if not name:
            return
        try:
            self.state.switch_profile(name)
        except KeyError:
            QMessageBox.warning(self, "Profile", f"未找到 Profile {name}")
            return
        self.refresh_views()

    def on_profile_add(self) -> None:
        name, ok = QInputDialog.getText(self, "新建 Profile", "名称")
        if not ok or not name:
            return
        profile = self.state.current_profile.model_copy() if self.state.current_profile else None
        if profile:
            profile.name = name
            self.state.current_profile = profile
            self.state.save_profile(profile)
            if self.profile_combo.findText(name) == -1:
                self.profile_combo.addItem(name)
            self.profile_combo.setCurrentText(name)

    def on_profile_save_as(self) -> None:
        if not self.state.current_profile:
            return
        name, ok = QInputDialog.getText(self, "另存为 Profile", "名称")
        if not ok or not name:
            return
        profile = self.state.current_profile.model_copy()
        profile.name = name
        self.state.current_profile = profile
        self.state.save_profile(profile)
        if self.profile_combo.findText(name) == -1:
            self.profile_combo.addItem(name)
        self.profile_combo.setCurrentText(name)

    # ------------------------------------------------------------------
    def _init_status_timer(self) -> None:
        self.refresh_status_bar()
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(60_000)
        self._status_timer.timeout.connect(self.refresh_status_bar)
        self._status_timer.start()

    # ------------------------------------------------------------------
    def refresh_status_bar(self) -> None:
        infos = self.secrets_service.list_all()
        if not infos:
            self.statusBar().showMessage("尚未导入登录态")
            return
        message = " | ".join(
            f"{item['name']}: D-{item['days_left']}"
            for item in infos
        )
        self.statusBar().showMessage(message)


__all__ = ["MainWindow"]
