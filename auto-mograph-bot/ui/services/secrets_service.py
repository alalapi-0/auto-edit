"""密钥存储服务，支持系统 keyring 与本地加密文件两种模式。"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import keyring

from ..utils import crypto


class SecretStorageError(Exception):
    """密钥存储操作失败。"""


class SecretBackend:
    """密钥存储后端抽象接口。"""

    name: str

    def set_secret(self, key: str, value: str) -> None:  # pragma: no cover - 接口
        raise NotImplementedError

    def get_secret(self, key: str) -> Optional[str]:  # pragma: no cover - 接口
        raise NotImplementedError

    def delete_secret(self, key: str) -> None:  # pragma: no cover - 接口
        raise NotImplementedError


@dataclass
class KeyringBackend(SecretBackend):
    """系统 keyring 后端实现。"""

    service_name: str
    name: str = "keyring"

    def set_secret(self, key: str, value: str) -> None:
        keyring.set_password(self.service_name, key, value)

    def get_secret(self, key: str) -> Optional[str]:
        try:
            return keyring.get_password(self.service_name, key)
        except keyring.errors.KeyringError as exc:  # pragma: no cover - 与系统有关
            raise SecretStorageError(str(exc)) from exc

    def delete_secret(self, key: str) -> None:
        try:
            keyring.delete_password(self.service_name, key)
        except keyring.errors.KeyringError:
            pass


class LocalEncryptedBackend(SecretBackend):
    """基于本地加密文件的密钥存储。"""

    name = "local_encrypted"

    def __init__(self, path: Path | str = Path("secrets/.secrets.json.enc")) -> None:
        self.path = Path(path)
        self._cache: Dict[str, str] | None = None
        self._password: Optional[str] = None
        self._salt: Optional[bytes] = None

    # ------------------------------------------------------------------
    def set_master_password(self, password: str) -> None:
        """设置或更新主密码。"""

        self._password = password
        if self.path.exists() and not self._salt:
            # 已有文件时需要保留原盐值
            content = self._read_raw_file()
            if content:
                try:
                    self._salt = base64.b64decode(content["salt"])
                    plaintext = crypto.decrypt_text(
                        base64.b64decode(content["token"]), password, salt=self._salt
                    )
                    self._cache = json.loads(plaintext)
                except (KeyError, crypto.EncryptionError) as exc:
                    raise SecretStorageError("主密码错误或文件损坏") from exc

    # ------------------------------------------------------------------
    def set_secret(self, key: str, value: str) -> None:
        store = self._ensure_store()
        store[key] = value
        self._persist(store)

    def get_secret(self, key: str) -> Optional[str]:
        store = self._ensure_store()
        return store.get(key)

    def delete_secret(self, key: str) -> None:
        store = self._ensure_store()
        if key in store:
            del store[key]
            self._persist(store)

    # ------------------------------------------------------------------
    def _ensure_store(self) -> Dict[str, str]:
        if self._cache is not None:
            return self._cache
        if not self._password:
            raise SecretStorageError("尚未设置主密码")
        if self.path.exists():
            content = self._read_raw_file()
            if content:
                self._salt = base64.b64decode(content["salt"])
                plaintext = crypto.decrypt_text(
                    base64.b64decode(content["token"]), self._password, salt=self._salt
                )
                self._cache = json.loads(plaintext)
                return self._cache
        self._cache = {}
        return self._cache

    def _persist(self, store: Dict[str, str]) -> None:
        if not self._password:
            raise SecretStorageError("尚未设置主密码")
        salt = self._salt or crypto.generate_salt()
        token_salt, token = crypto.encrypt_text(
            json.dumps(store, ensure_ascii=False), self._password, salt=salt
        )
        self._salt = token_salt
        payload = {
            "salt": base64.b64encode(token_salt).decode("utf-8"),
            "token": base64.b64encode(token).decode("utf-8"),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def _read_raw_file(self) -> Dict[str, str]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)


class SecretsService:
    """统一密钥管理入口。"""

    def __init__(self, backend: SecretBackend) -> None:
        self.backend = backend

    def set_secret(self, key: str, value: str) -> None:
        self.backend.set_secret(key, value)

    def get_secret(self, key: str) -> Optional[str]:
        return self.backend.get_secret(key)

    def delete_secret(self, key: str) -> None:
        self.backend.delete_secret(key)

    def replace_backend(self, backend: SecretBackend) -> None:
        self.backend = backend


__all__ = [
    "SecretStorageError",
    "SecretBackend",
    "KeyringBackend",
    "LocalEncryptedBackend",
    "SecretsService",
]
