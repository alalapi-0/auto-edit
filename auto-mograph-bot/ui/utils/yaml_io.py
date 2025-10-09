"""YAML 文件读写工具，带基础的 schema 校验支持。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import yaml
from pydantic import BaseModel, ValidationError


class YamlValidationError(Exception):
    """表示 YAML 文件内容不符合预期结构。"""

    def __init__(self, path: Path | str, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = Path(path)
        self.message = message


def load_yaml_file(path: Path | str) -> Any:
    """加载 YAML 文件并返回 Python 对象。"""

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"未找到 YAML 文件: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def dump_yaml_file(data: Any, path: Path | str) -> None:
    """将数据写入 YAML 文件。"""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=False)


def validate_yaml_with_model(
    data: Any,
    model: type[BaseModel],
    *,
    path: Optional[Path | str] = None,
) -> BaseModel:
    """使用 Pydantic 模型对数据进行校验。"""

    try:
        return model.model_validate(data)
    except ValidationError as exc:  # pragma: no cover - 仅在运行时报错
        raise YamlValidationError(path or Path("<memory>"), str(exc)) from exc


def merge_yaml_documents(documents: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """合并多个 YAML 字典，后者覆盖前者。"""

    result: Dict[str, Any] = {}
    for document in documents:
        if not isinstance(document, dict):
            continue
        result.update(document)
    return result


__all__ = [
    "YamlValidationError",
    "load_yaml_file",
    "dump_yaml_file",
    "validate_yaml_with_model",
    "merge_yaml_documents",
]
