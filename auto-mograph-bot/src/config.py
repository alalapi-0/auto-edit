"""Configuration loader for Auto Mograph Bot."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, validator
import yaml


class VideoSettings(BaseModel):
    width: int = 1080
    height: int = 1920
    fps: int = 30
    duration: float = 8.0

    @validator("width", "height", "fps")
    def validate_positive_int(cls, value: int) -> int:  # noqa: D401
        """Ensure numeric values are positive."""
        if value <= 0:
            raise ValueError("Video dimension values must be positive")
        return value

    @validator("duration")
    def validate_duration(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Video duration must be positive")
        return value


@dataclass
class ModelPaths:
    txt2img: Optional[Path] = None
    img2vid: Optional[Path] = None
    embeddings: Optional[Path] = None


@dataclass
class PipelineConfig:
    video: VideoSettings = field(default_factory=VideoSettings)
    model_paths: ModelPaths = field(default_factory=ModelPaths)
    prompt_pool_path: Optional[Path] = None

    extra: Dict[str, Any] = field(default_factory=dict)


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        return yaml.safe_load(fp) or {}


def merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {**base}
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_path: Optional[Path] = None, env_path: Optional[Path] = None) -> PipelineConfig:
    """Load configuration from YAML and `.env` files."""

    if env_path is None:
        env_path = Path(".env")
    load_dotenv(dotenv_path=env_path, override=False)

    if config_path is None:
        config_path = Path("configs/default.yaml")

    data = load_yaml(config_path)

    video_data = data.get("video", {})
    model_data = data.get("model_paths", {})
    extra = {key: value for key, value in data.items() if key not in {"video", "model_paths"}}

    video_settings = VideoSettings(**video_data)
    model_paths = ModelPaths(**{k: Path(v) if v else None for k, v in model_data.items()})

    return PipelineConfig(
        video=video_settings,
        model_paths=model_paths,
        prompt_pool_path=Path(data["prompt_pool_path"]) if data.get("prompt_pool_path") else None,
        extra=extra,
    )


__all__ = ["PipelineConfig", "VideoSettings", "ModelPaths", "load_config"]
