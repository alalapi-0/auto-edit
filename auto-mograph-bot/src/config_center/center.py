"""Unified configuration center for CLI and GUI components."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from types import MappingProxyType
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel


def _load_yaml(path: Path) -> Dict[str, Any]:
    """Load a YAML file if it exists, returning an empty dict otherwise."""

    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}
        if not isinstance(data, MutableMapping):
            raise TypeError(f"YAML {path} must contain a mapping at the top level")
        return dict(data)


def _merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two dictionaries and return the merged result."""

    result: Dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def _freeze(value: Any) -> Any:
    """Create an immutable view for the given value."""

    if isinstance(value, dict):
        frozen = {key: _freeze(inner) for key, inner in value.items()}
        return MappingProxyType(frozen)
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _write_yaml_atomic(path: Path, data: Mapping[str, Any]) -> None:
    """Write YAML atomically to avoid partially written files."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as tmp:
        yaml.safe_dump(data, tmp, allow_unicode=True, sort_keys=False)
        temp_name = tmp.name
    os.replace(temp_name, path)


class ConfigCenter:
    """Centralises configuration loading, validation and profile management."""

    def __init__(self, model_cls: Optional[type[BaseModel]] = None) -> None:
        self._model_cls = model_cls
        self._model: Optional[BaseModel] = None
        self._raw: Dict[str, Any] = {}
        self._frozen: Mapping[str, Any] = MappingProxyType({})
        self._base_paths: list[str] = ["configs/default.yaml"]
        self._extra_paths: list[str] = []
        self._env_path: Optional[Path] = Path(".env")
        self._default_snapshot: Dict[str, Any] = {}
        self._profiles_dir: Path = Path("profiles")

    # ------------------------------------------------------------------
    def load(
        self,
        *,
        base_paths: Optional[Iterable[str]] = None,
        extra_paths: Optional[Iterable[str]] = None,
        env_path: Optional[str] = None,
    ) -> Mapping[str, Any]:
        """Load configuration files and environment overrides."""

        if base_paths is not None:
            self._base_paths = [str(Path(p)) for p in base_paths]
        if extra_paths is not None:
            self._extra_paths = [str(Path(p)) for p in extra_paths]
        if env_path is not None:
            self._env_path = Path(env_path)
        elif self._env_path is None:
            self._env_path = Path(".env")

        if self._env_path and self._env_path.exists():
            load_dotenv(self._env_path, override=False)

        ordered_paths = self._base_paths + self._extra_paths
        data: Dict[str, Any] = {}
        for idx, path_str in enumerate(ordered_paths):
            yaml_data = _load_yaml(Path(path_str))
            if idx == 0:
                self._default_snapshot = yaml_data
            data = _merge_dict(data, yaml_data)

        data = _merge_dict(data, self._build_env_override())
        self._raw = data
        self._frozen = _freeze(data)

        if self._model_cls is not None:
            self._model = self._model_cls.model_validate(data)
        else:
            self._model = None

        profiles_cfg = data.get("profiles", {})
        if isinstance(profiles_cfg, Mapping):
            directory = profiles_cfg.get("dir")
            if isinstance(directory, str) and directory:
                self._profiles_dir = Path(directory)
        self._profiles_dir.mkdir(parents=True, exist_ok=True)
        return self.get()

    # ------------------------------------------------------------------
    def reload(self) -> Mapping[str, Any]:
        """Reload with the last used parameters."""

        return self.load(
            base_paths=self._base_paths,
            extra_paths=self._extra_paths,
            env_path=str(self._env_path) if self._env_path else None,
        )

    # ------------------------------------------------------------------
    def get(self) -> Mapping[str, Any]:
        """Return an immutable view of the merged configuration."""

        return self._frozen

    # ------------------------------------------------------------------
    def get_raw(self) -> Dict[str, Any]:
        """Return a mutable copy of the merged configuration."""

        return dict(self._raw)

    # ------------------------------------------------------------------
    def get_model(self) -> Optional[BaseModel]:
        """Return the validated Pydantic model, if any."""

        return self._model

    # ------------------------------------------------------------------
    @property
    def profile_directory(self) -> Path:
        """Return the directory used to store profile YAML files."""

        return self._profiles_dir

    # ------------------------------------------------------------------
    def validate(self, payload: Mapping[str, Any]) -> BaseModel:
        """Validate a configuration payload using the configured model class."""

        if self._model_cls is None:
            raise RuntimeError("ConfigCenter was initialised without a model class")
        merged = _merge_dict(dict(self._default_snapshot), dict(payload))
        return self._model_cls.model_validate(merged)

    # ------------------------------------------------------------------
    def export_profile(self, name: str, path: str) -> Path:
        """Export the current configuration as a profile YAML."""

        if not name:
            raise ValueError("Profile name cannot be empty")
        if not self._raw:
            raise RuntimeError("Configuration has not been loaded")
        target = Path(path)
        payload = {
            "profile": {
                "name": name,
            },
            "config": self._raw,
        }
        _write_yaml_atomic(target, payload)
        return target

    # ------------------------------------------------------------------
    def import_profile(self, path: str) -> Path:
        """Import a profile YAML and store it under configs/NAME.yaml."""

        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(f"Profile source {source} does not exist")
        with source.open("r", encoding="utf-8") as fp:
            payload = yaml.safe_load(fp) or {}
        if not isinstance(payload, Mapping):
            raise TypeError("Imported profile must contain a mapping")
        profile_meta = payload.get("profile", {})
        if isinstance(profile_meta, Mapping):
            name = str(profile_meta.get("name") or source.stem)
        else:
            name = source.stem
        config_data = payload.get("config") if "config" in payload else payload
        if not isinstance(config_data, Mapping):
            raise TypeError("Profile config section 必须为映射类型")
        base = self._default_snapshot or {}
        merged = _merge_dict(base, dict(config_data))
        target = Path("configs") / f"{name}.yaml"
        _write_yaml_atomic(target, merged)

        if str(target) not in self._extra_paths:
            self._extra_paths = [*self._extra_paths, str(target)]
        self.reload()
        return target

    # ------------------------------------------------------------------
    def _build_env_override(self) -> Dict[str, Any]:
        """Construct overrides sourced from environment variables."""

        override: Dict[str, Any] = {
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
                "dry_run": str(os.getenv("DRY_RUN", "false")).lower() == "true",
            },
        }
        # Remove None values to avoid overriding explicit configuration
        for section in list(override.keys()):
            cleaned: Dict[str, Any] = {}
            for key, value in override[section].items():
                if value is not None:
                    cleaned[key] = value
            if cleaned:
                override[section] = cleaned
            else:
                override.pop(section)
        return override


__all__ = ["ConfigCenter"]
