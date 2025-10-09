"""生成参数表单。"""
from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QSpinBox,
    QDoubleSpinBox,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
)

from ...state import AppState, PipelineSettings, Resolution


class PipelineForm(QWidget):
    """生成参数配置组件。"""

    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = state

        self.width_spin = QSpinBox(self)
        self.width_spin.setRange(16, 8192)
        self.width_spin.setValue(1920)

        self.height_spin = QSpinBox(self)
        self.height_spin.setRange(16, 8192)
        self.height_spin.setValue(1080)

        self.fps_spin = QSpinBox(self)
        self.fps_spin.setRange(1, 240)
        self.duration_spin = QDoubleSpinBox(self)
        self.duration_spin.setRange(0.5, 600)
        self.duration_spin.setDecimals(1)

        self.crf_spin = QSpinBox(self)
        self.crf_spin.setRange(0, 51)

        self.pix_fmt_edit = QLineEdit(self)
        self.preset_edit = QLineEdit(self)
        self.seed_edit = QLineEdit(self)
        self.text_edit = QLineEdit(self)
        self.font_edit = QLineEdit(self)

        self.save_button = QPushButton("保存", self)
        self.reset_button = QPushButton("恢复默认", self)

        layout = QFormLayout()
        layout.addRow("宽度", self.width_spin)
        layout.addRow("高度", self.height_spin)
        layout.addRow("FPS", self.fps_spin)
        layout.addRow("时长(秒)", self.duration_spin)
        layout.addRow("CRF", self.crf_spin)
        layout.addRow("像素格式", self.pix_fmt_edit)
        layout.addRow("动作预设", self.preset_edit)
        layout.addRow("Seed", self.seed_edit)
        layout.addRow("文案", self.text_edit)
        layout.addRow("字体路径", self.font_edit)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.reset_button)
        layout.addRow(button_layout)
        self.setLayout(layout)

        self._load_from_state()
        self.save_button.clicked.connect(self.on_save)
        self.reset_button.clicked.connect(self.on_reset)

    def _load_from_state(self) -> None:
        profile = self.state.current_profile
        if not profile:
            return
        pipeline = profile.pipeline
        self.width_spin.setValue(pipeline.resolution.width)
        self.height_spin.setValue(pipeline.resolution.height)
        self.fps_spin.setValue(pipeline.fps)
        self.duration_spin.setValue(pipeline.duration)
        self.crf_spin.setValue(pipeline.crf)
        self.pix_fmt_edit.setText(pipeline.pix_fmt)
        self.preset_edit.setText(pipeline.preset)
        self.seed_edit.setText("" if pipeline.seed is None else str(pipeline.seed))
        self.text_edit.setText(pipeline.text)
        self.font_edit.setText(pipeline.subtitle_font or "")

    def refresh(self) -> None:
        """刷新表单。"""

        self._load_from_state()

    @Slot()
    def on_save(self) -> None:
        profile = self.state.current_profile
        if not profile:
            return
        seed_text = self.seed_edit.text().strip()
        pipeline = PipelineSettings(
            resolution=Resolution(
                width=self.width_spin.value(),
                height=self.height_spin.value(),
            ),
            fps=self.fps_spin.value(),
            duration=self.duration_spin.value(),
            crf=self.crf_spin.value(),
            pix_fmt=self.pix_fmt_edit.text().strip() or "yuv420p",
            preset=self.preset_edit.text().strip() or "default",
            seed=int(seed_text) if seed_text else None,
            text=self.text_edit.text(),
            subtitle_font=self.font_edit.text().strip() or None,
        )
        updated = profile.model_copy(update={"pipeline": pipeline.model_dump()})
        self.state.save_profile(updated)
        QMessageBox.information(self, "成功", "生成参数已保存")

    @Slot()
    def on_reset(self) -> None:
        defaults = PipelineSettings()
        self.width_spin.setValue(defaults.resolution.width)
        self.height_spin.setValue(defaults.resolution.height)
        self.fps_spin.setValue(defaults.fps)
        self.duration_spin.setValue(defaults.duration)
        self.crf_spin.setValue(defaults.crf)
        self.pix_fmt_edit.setText(defaults.pix_fmt)
        self.preset_edit.setText(defaults.preset)
        self.seed_edit.clear()
        self.text_edit.clear()
        self.font_edit.clear()
        if self.state.current_profile:
            profile = self.state.current_profile.model_copy(update={"pipeline": defaults.model_dump()})
            self.state.save_profile(profile)


__all__ = ["PipelineForm"]
