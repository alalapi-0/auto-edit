"""配置加载模块，负责读取 YAML 与环境变量并生成统一的运行配置对象。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator
import yaml


class VideoSettings(BaseModel):
    """视频导出相关参数配置。"""

    width: int = Field(1080, description="导出视频宽度")
    height: int = Field(1920, description="导出视频高度")
    fps: int = Field(24, description="导出帧率")
    duration: float = Field(6.0, description="导出视频时长（秒）")
    crf: int = Field(18, description="H.264 恒定质量因子")
    bitrate: Optional[str] = Field("8M", description="视频码率，可选，单位如 8M")
    audio_bitrate: str = Field("192k", description="音频码率设置")
    preset: str = Field("medium", description="FFmpeg x264 预设")
    cover_export: bool = Field(False, description="是否导出封面帧")
    cover_timecode: float = Field(0.0, description="封面帧截取时间点（秒）")
    vertical_safe_margin: int = Field(120, description="竖屏文字安全区边距像素")

    @validator("width", "height", "fps", "crf", "vertical_safe_margin")
    def validate_positive_int(cls, value: int) -> int:  # noqa: D401
        """确保整数参数为正数。"""

        if value <= 0:
            raise ValueError("视频尺寸、帧率等整数参数必须大于 0")
        return value

    @validator("duration", "cover_timecode")
    def validate_positive_float(cls, value: float) -> float:
        if value < 0:
            raise ValueError("视频时长或时间点不能为负数")
        return value


class PromptSettings(BaseModel):
    """文案池与安全过滤相关配置。"""

    extra_texts: List[str] = Field(default_factory=list, description="额外文案")
    extra_styles: List[str] = Field(default_factory=list, description="额外风格")
    extra_tags: List[str] = Field(default_factory=list, description="额外标签")
    blacklist_topics: List[str] = Field(default_factory=list, description="主题黑名单")
    sensitive_words: List[str] = Field(default_factory=list, description="敏感词列表")
    max_title_length: int = Field(30, description="投稿标题最大长度（字符）")
    max_desc_length: int = Field(120, description="投稿描述最大长度（字符）")
    max_tags: int = Field(5, description="投稿标签数量上限")


class SDBackendSettings(BaseModel):
    """Stable Diffusion 文本生图参数。"""

    backend: str = Field("diffusers", description="可选 diffusers 或 webui")
    model_path: Optional[Path] = Field(None, description="本地模型路径")
    vae_path: Optional[Path] = Field(None, description="VAE 模型路径")
    lora_paths: List[Path] = Field(default_factory=list, description="LoRA 路径列表")
    sampler: str = Field("ddim", description="采样器名称")
    guidance_scale: float = Field(7.5, description="提示词权重")
    steps: int = Field(30, description="采样步数")
    seed: Optional[int] = Field(None, description="固定随机种子")
    webui_url: Optional[str] = Field(None, description="SD WebUI 接口地址")
    webui_token: Optional[str] = Field(None, description="SD WebUI 鉴权 Token")

    @validator("backend")
    def validate_backend(cls, value: str) -> str:
        valid = {"diffusers", "webui"}
        if value not in valid:
            raise ValueError(f"backend 仅支持 {valid}")
        return value


class AnimateSettings(BaseModel):
    """AnimateDiff / Stable Video Diffusion 参数。"""

    backend: str = Field("animatediff", description="可选 animatediff 或 svd")
    model_path: Optional[Path] = Field(None, description="视频模型权重路径")
    motion_module: Optional[Path] = Field(None, description="AnimateDiff 动作模块")
    num_frames: int = Field(144, description="生成帧数，24fps * 6s")
    fps: int = Field(24, description="视频模型输出帧率")
    strength: float = Field(0.65, description="运动强度/CFG")
    seed: Optional[int] = Field(None, description="随机种子")

    @validator("backend")
    def validate_backend(cls, value: str) -> str:
        valid = {"animatediff", "svd"}
        if value not in valid:
            raise ValueError(f"video backend 仅支持 {valid}")
        return value


class AudioSettings(BaseModel):
    """音频/BGM 设置。"""

    enable_bgm: bool = Field(False, description="是否自动添加静音 BGM 或提示音")
    bgm_directory: Path = Field(Path("assets/sfx"), description="BGM 目录")
    normalize: bool = Field(True, description="是否归一化音量")
    volume: float = Field(0.6, description="混合到主轨的音量倍率")


class SchedulerSettings(BaseModel):
    """批量任务调度设置。"""

    batch_size: int = Field(1, description="每轮生成的任务数")
    concurrency: int = Field(1, description="并发度（受显存限制，建议串行）")
    min_free_vram_mb: int = Field(3000, description="单个任务所需的最小空闲显存(MB)")
    hard_serial: bool = Field(True, description="显存不足时是否强制串行执行")
    max_retries: int = Field(2, description="失败重试次数")
    cooldown_sec: float = Field(3.0, description="重试前冷却时间")
    index_file: Path = Field(Path("outputs/index.jsonl"), description="产物索引 JSONL 文件路径")
    log_dir: Path = Field(Path("outputs/logs"), description="日志输出目录")
    lock_path: Path = Field(Path("locks/gpu.lock"), description="并发互斥锁文件路径")

    @validator("batch_size", "concurrency", "max_retries")
    def validate_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("批量参数必须大于 0")
        return value

    @validator("min_free_vram_mb")
    def validate_min_vram(cls, value: int) -> int:
        if value < 0:
            raise ValueError("最小空闲显存需求不能为负数")
        return value

    @validator("cooldown_sec")
    def validate_cooldown(cls, value: float) -> float:
        if value < 0:
            raise ValueError("冷却时间不能为负数")
        return value


class StorageSettings(BaseModel):
    """输入输出路径配置。"""

    output_dir: Path = Field(Path("outputs"), description="视频输出目录")
    cover_dir: Path = Field(Path("outputs/covers"), description="封面输出目录")
    frames_dir: Path = Field(Path("outputs/frames"), description="临时帧目录")
    tmp_dir: Path = Field(Path("outputs/tmp"), description="临时文件目录")


class UploaderSettings(BaseModel):
    """上传模块配置。"""

    provider: str = Field("none", description="当前启用的上传 Provider")
    target: Optional[str] = Field(None, description="目标平台标识")
    visibility: str = Field("private", description="上传后的视频可见性")
    cookie_path: Optional[Path] = Field(None, description="Cookie 文件路径，用于 Web 自动化")
    api_token: Optional[str] = Field(None, description="官方 API Token")
    appium_server: Optional[str] = Field(None, description="Appium 服务器地址")
    device_name: Optional[str] = Field(None, description="移动端设备名称")
    extra: Dict[str, Any] = Field(default_factory=dict, description="额外 Provider 配置")


class SafetySettings(BaseModel):
    """内容安全相关配置。"""

    enable_sensitive_scan: bool = Field(True, description="是否启用敏感词检测")
    enable_ad_scan: bool = Field(True, description="是否检测广告词")
    retry_on_violation: bool = Field(False, description="触发敏感词后是否重试抽取文案")


class RuntimeSettings(BaseModel):
    """运行时控制参数。"""

    seed: Optional[int] = Field(None, description="全局随机种子")
    dry_run: bool = Field(False, description="是否仅输出指令不实际调用重量模型")


class ConfigModel(BaseModel):
    """顶层配置模型。"""

    video: VideoSettings = Field(default_factory=VideoSettings)
    prompts: PromptSettings = Field(default_factory=PromptSettings)
    sd: SDBackendSettings = Field(default_factory=SDBackendSettings)
    animate: AnimateSettings = Field(default_factory=AnimateSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    uploader: UploaderSettings = Field(default_factory=UploaderSettings)
    safety: SafetySettings = Field(default_factory=SafetySettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)


@dataclass
class PipelineConfig:
    """供流水线消费的配置对象。"""

    model: ConfigModel
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def video(self) -> VideoSettings:
        return self.model.video

    @property
    def prompts(self) -> PromptSettings:
        return self.model.prompts

    @property
    def sd(self) -> SDBackendSettings:
        return self.model.sd

    @property
    def animate(self) -> AnimateSettings:
        return self.model.animate

    @property
    def audio(self) -> AudioSettings:
        return self.model.audio

    @property
    def scheduler(self) -> SchedulerSettings:
        return self.model.scheduler

    @property
    def storage(self) -> StorageSettings:
        return self.model.storage

    @property
    def uploader(self) -> UploaderSettings:
        return self.model.uploader

    @property
    def safety(self) -> SafetySettings:
        return self.model.safety

    @property
    def runtime(self) -> RuntimeSettings:
        return self.model.runtime

    @property
    def prompt_pool_path(self) -> Optional[Path]:
        """返回文案池外部文件路径。"""

        value = self.raw_data.get("prompt_pool_path")
        if value:
            return Path(value)
        return None


def _load_yaml_config(path: Path) -> Dict[str, Any]:
    """读取 YAML 文件内容，若为空则返回空字典。"""

    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fp:
        return yaml.safe_load(fp) or {}


def _merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """递归合并配置字典，override 优先。"""

    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_path: Optional[Path] = None, env_path: Optional[Path] = None) -> PipelineConfig:
    """加载配置：优先读取 .env，再解析 YAML，并生成 PipelineConfig。"""

    if env_path is None:
        env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path, override=False)

    if config_path is None:
        config_path = Path("configs/default.yaml")

    yaml_config = _load_yaml_config(config_path)

    env_override: Dict[str, Any] = {
        "sd": {
            "webui_url": os.getenv("SD_WEBUI_URL"),
            "webui_token": os.getenv("SD_WEBUI_TOKEN"),
            "model_path": Path(os.getenv("SD_MODEL_PATH")) if os.getenv("SD_MODEL_PATH") else None,
        },
        "animate": {
            "model_path": Path(os.getenv("ANIMATEDIFF_MODEL_PATH")) if os.getenv("ANIMATEDIFF_MODEL_PATH") else None,
            "motion_module": Path(os.getenv("ANIMATEDIFF_MOTION_PATH")) if os.getenv("ANIMATEDIFF_MOTION_PATH") else None,
        },
        "uploader": {
            "api_token": os.getenv("UPLOADER_API_TOKEN"),
            "cookie_path": Path(os.getenv("UPLOADER_COOKIE_PATH")) if os.getenv("UPLOADER_COOKIE_PATH") else None,
            "appium_server": os.getenv("APPIUM_SERVER"),
            "device_name": os.getenv("APPIUM_DEVICE_NAME"),
        },
        "runtime": {
            "seed": int(os.getenv("GLOBAL_SEED")) if os.getenv("GLOBAL_SEED") else None,
            "dry_run": os.getenv("DRY_RUN", "false").lower() == "true",
        },
    }

    merged = _merge_dict(yaml_config, env_override)
    model = ConfigModel.model_validate(merged)

    # 规范化路径，确保目录存在
    for path_attr in [
        model.storage.output_dir,
        model.storage.cover_dir,
        model.storage.frames_dir,
        model.storage.tmp_dir,
        model.scheduler.log_dir,
        model.scheduler.index_file.parent,
        model.scheduler.lock_path.parent,
    ]:
        Path(path_attr).mkdir(parents=True, exist_ok=True)

    return PipelineConfig(model=model, raw_data=merged)


__all__ = [
    "PipelineConfig",
    "ConfigModel",
    "VideoSettings",
    "PromptSettings",
    "SDBackendSettings",
    "AnimateSettings",
    "AudioSettings",
    "SchedulerSettings",
    "StorageSettings",
    "UploaderSettings",
    "SafetySettings",
    "RuntimeSettings",
    "load_config",
]
