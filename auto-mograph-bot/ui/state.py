"""应用全局状态与配置模型定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError, root_validator

from .utils import yaml_io


class Resolution(BaseModel):
    """视频分辨率设置。"""

    width: int = Field(1920, ge=16, description="视频宽度像素值")
    height: int = Field(1080, ge=16, description="视频高度像素值")


class PipelineSettings(BaseModel):
    """生成流水线相关参数。"""

    resolution: Resolution = Field(default_factory=Resolution)
    fps: int = Field(30, ge=1, le=120, description="生成视频的帧率")
    duration: float = Field(6.0, gt=0, description="视频时长，单位秒")
    crf: int = Field(18, ge=0, le=51, description="FFmpeg CRF 值")
    pix_fmt: str = Field("yuv420p", description="像素格式")
    preset: str = Field("default", description="动作预设名称")
    seed: Optional[int] = Field(None, description="随机种子，空表示随机")
    text: str = Field("", description="生成使用的文案文本")
    subtitle_font: Optional[str] = Field(
        None, description="字幕字体文件路径，None 表示使用默认字体"
    )


class UploaderSettings(BaseModel):
    """上传配置。"""

    platform: str = Field("douyin", description="目标平台")
    provider: str = Field("web", description="上传方式提供者")
    storage_state_path: Optional[str] = Field(
        None, description="Playwright storage_state JSON 文件路径"
    )
    appium_server: Optional[str] = Field(
        None, description="Appium Server 地址，当 provider 为 appium 时使用"
    )
    extra: Dict[str, str] = Field(
        default_factory=dict, description="额外参数，如 API Token 等"
    )


class DatabaseSettings(BaseModel):
    """数据库连接配置。"""

    backend: str = Field("sqlite", description="数据库类型：sqlite/mysql/postgres")
    dsn: str = Field("sqlite:///./mograph.db", description="SQLAlchemy 连接串")


class VPSSettings(BaseModel):
    """VPS Provider 配置。"""

    provider: str = Field("local", description="当前选择的 Provider")
    options: Dict[str, str] = Field(
        default_factory=dict, description="Provider 额外参数，例如 API Key"
    )


class Profile(BaseModel):
    """运行配置档案(Profile)。"""

    name: str = Field(..., description="Profile 名称，例如 dev-local")
    description: Optional[str] = Field(None, description="Profile 说明")
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)
    uploader: UploaderSettings = Field(default_factory=UploaderSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    vps: VPSSettings = Field(default_factory=VPSSettings)

    @root_validator(pre=True)
    def fill_missing_name(cls, values: Dict[str, object]) -> Dict[str, object]:
        """允许配置文件缺省 name 字段时使用文件名占位。"""

        if not values.get("name") and "__source_name__" in values:
            values["name"] = values["__source_name__"]
        return values


@dataclass
class RuntimeTask:
    """用于记录 UI 中的实时任务信息。"""

    task_id: str
    command: List[str]
    log_buffer: List[str] = field(default_factory=list)
    is_running: bool = True
    exit_code: Optional[int] = None


class AppState:
    """管理 UI 运行时状态、配置档案与实时任务。"""

    def __init__(
        self,
        config_dir: Path | str = Path("configs"),
        profiles_dir: Path | str = Path("profiles"),
    ) -> None:
        self.config_dir = Path(config_dir)
        self.profiles_dir = Path(profiles_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.secrets_dir = Path("secrets")
        self.secrets_dir.mkdir(exist_ok=True)

        self.profiles: Dict[str, Profile] = {}
        self.current_profile: Optional[Profile] = None
        self.runtime_tasks: Dict[str, RuntimeTask] = {}

        self._load_all_profiles()
        if not self.current_profile and self.profiles:
            # 默认使用首个 profile
            first_profile = next(iter(self.profiles.values()))
            self.current_profile = first_profile
        elif not self.profiles:
            # 创建一个默认 profile
            default_profile = Profile(name="default")
            self.profiles[default_profile.name] = default_profile
            self.current_profile = default_profile
            self.save_profile(default_profile)

    # ------------------------------------------------------------------
    # Profile 相关操作
    # ------------------------------------------------------------------
    def _load_all_profiles(self) -> None:
        """从 profiles 目录加载所有配置文件。"""

        for path in self.profiles_dir.glob("*.yaml"):
            try:
                data = yaml_io.load_yaml_file(path)
                if isinstance(data, dict):
                    data.setdefault("__source_name__", path.stem)
                    profile = Profile.model_validate(data)
                    self.profiles[profile.name] = profile
            except (yaml_io.YamlValidationError, ValidationError) as exc:
                print(f"加载 Profile {path} 失败: {exc}")

    def list_profiles(self) -> List[str]:
        """返回可用 Profile 名称列表。"""

        return sorted(self.profiles.keys())

    def save_profile(self, profile: Profile) -> Path:
        """保存 Profile 到 YAML 文件。"""

        target = self.profiles_dir / f"{profile.name}.yaml"
        yaml_io.dump_yaml_file(profile.model_dump(mode="json"), target)
        self.profiles[profile.name] = profile
        if self.current_profile and self.current_profile.name == profile.name:
            self.current_profile = profile
        return target

    def switch_profile(self, name: str) -> Profile:
        """切换当前 Profile。"""

        if name not in self.profiles:
            raise KeyError(f"Profile '{name}' 不存在")
        self.current_profile = self.profiles[name]
        return self.current_profile

    def update_current_profile(self, **updates: object) -> Profile:
        """更新当前 Profile 的部分字段。"""

        if not self.current_profile:
            raise RuntimeError("当前没有选中的 Profile")
        data = self.current_profile.model_dump()
        for key, value in updates.items():
            if key in data and isinstance(value, dict):
                data[key].update(value)
            else:
                data[key] = value
        updated = Profile.model_validate(data)
        self.current_profile = updated
        self.save_profile(updated)
        return updated

    # ------------------------------------------------------------------
    # 任务追踪
    # ------------------------------------------------------------------
    def register_task(self, task: RuntimeTask) -> None:
        """记录一个运行中的任务。"""

        self.runtime_tasks[task.task_id] = task

    def update_task_log(self, task_id: str, line: str) -> None:
        """追加任务日志。"""

        task = self.runtime_tasks.get(task_id)
        if task:
            task.log_buffer.append(line)

    def complete_task(self, task_id: str, exit_code: int) -> None:
        """标记任务完成。"""

        task = self.runtime_tasks.get(task_id)
        if task:
            task.is_running = False
            task.exit_code = exit_code


__all__ = [
    "AppState",
    "Profile",
    "PipelineSettings",
    "UploaderSettings",
    "DatabaseSettings",
    "VPSSettings",
    "RuntimeTask",
]
