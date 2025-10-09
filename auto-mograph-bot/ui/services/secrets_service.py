"""安全加密存储服务：支持 Keyring 与 Fernet 双模式。"""
from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import keyring
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.security import expiry


class SecretsError(Exception):
    """密钥存储通用异常。"""


class SecretsBackendError(SecretsError):
    """后端操作失败。"""


class SecretsLockedError(SecretsError):
    """尚未设置主密码或主密码未解锁。"""


class SecretsNotFoundError(SecretsError):
    """指定条目不存在。"""


class SecretsExpiredError(SecretsError):
    """条目已过期。"""


class SecretsService:
    """安全加密存储服务：支持 Keyring 与 Fernet 双模式。"""

    VAULT_PATH = Path("secrets/.vault.enc")
    KEYRING_SERVICE = "auto-mograph-bot"
    KEYRING_ENTRY = "__vault_ciphertext__"
    KEYRING_SALT_ENTRY = "__vault_salt__"
    DEFAULT_TTL_DAYS = 30

    _shared_master_key: Optional[bytes] = None
    _shared_salt: Optional[bytes] = None
    _shared_backend: str = "fernet"
    _shared_cache: Optional[Dict[str, Dict[str, str]]] = None

    def __init__(self, backend: Optional[str] = None) -> None:
        if backend:
            self.use_backend(backend)

    # ------------------------------------------------------------------
    @property
    def backend(self) -> str:
        return type(self)._shared_backend

    # ------------------------------------------------------------------
    def use_backend(self, backend: str) -> None:
        backend = backend.lower().strip()
        if backend not in {"fernet", "keyring"}:
            raise SecretsError(f"未知的后端: {backend}")
        type(self)._shared_backend = backend
        type(self)._shared_cache = None
        type(self)._shared_salt = None
        type(self)._shared_master_key = None

    # ------------------------------------------------------------------
    def set_master_password(self, password: str) -> None:
        if not password:
            raise SecretsError("主密码不能为空。")
        salt = self._load_or_create_salt()
        master_key = self._derive_key(password, salt)
        type(self)._shared_master_key = master_key
        type(self)._shared_salt = salt
        try:
            self._load_entries(force_reload=True)
        except SecretsError as exc:
            type(self)._shared_master_key = None
            raise SecretsError("主密码错误或密钥库已损坏。") from exc
        if self.backend == "fernet" and not self.VAULT_PATH.exists():
            self._persist_entries({})
        elif self.backend == "keyring":
            if self._read_keyring_ciphertext() is None:
                self._persist_entries({})

    # ------------------------------------------------------------------
    def store(self, name: str, data: bytes, ttl_days: int = DEFAULT_TTL_DAYS) -> None:
        if not name:
            raise SecretsError("名称不能为空。")
        if ttl_days <= 0:
            raise SecretsError("有效期必须为正数。")
        entries = self._load_entries()
        payload = base64.b64encode(data).decode("utf-8")
        now = datetime.utcnow().isoformat()
        entries[name] = {
            "created_at": now,
            "ttl_days": ttl_days,
            "payload": payload,
        }
        self._persist_entries(entries)

    # ------------------------------------------------------------------
    def load(self, name: str) -> bytes:
        entries = self._load_entries()
        if name not in entries:
            raise SecretsNotFoundError(f"未找到条目 {name}")
        entry = entries[name]
        created_at = datetime.fromisoformat(entry["created_at"])
        ttl_days = int(entry.get("ttl_days", self.DEFAULT_TTL_DAYS))
        if expiry.is_expired(created_at, ttl_days):
            raise SecretsExpiredError(f"{name} 已过期")
        return base64.b64decode(entry["payload"])  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    def delete(self, name: str) -> None:
        entries = self._load_entries()
        if name in entries:
            del entries[name]
            self._persist_entries(entries)

    # ------------------------------------------------------------------
    def list_all(self) -> List[Dict[str, object]]:
        try:
            entries = self._load_entries()
        except SecretsLockedError:
            return []
        result: List[Dict[str, object]] = []
        for name, entry in entries.items():
            try:
                created_at = datetime.fromisoformat(entry["created_at"])
                ttl_days = int(entry.get("ttl_days", self.DEFAULT_TTL_DAYS))
            except (KeyError, ValueError) as exc:  # pragma: no cover - 容错
                raise SecretsError("密钥库格式错误。") from exc
            result.append(
                {
                    "name": name,
                    "created_at": created_at.isoformat(),
                    "ttl_days": ttl_days,
                    "days_left": expiry.days_left(created_at, ttl_days),
                    "is_expired": expiry.is_expired(created_at, ttl_days),
                }
            )
        result.sort(key=lambda item: item["name"])
        return result

    # ------------------------------------------------------------------
    def _load_entries(self, *, force_reload: bool = False) -> Dict[str, Dict[str, str]]:
        if not force_reload and type(self)._shared_cache is not None:
            return type(self)._shared_cache or {}
        master_key = self._ensure_master_key()
        salt = self._ensure_salt()
        if self.backend == "fernet":
            payload = self._read_vault_file()
            ciphertext = payload.get("ciphertext")
            if not ciphertext:
                entries: Dict[str, Dict[str, str]] = {}
            else:
                token = base64.b64decode(ciphertext)
                entries = self._decrypt_entries(token)
        else:
            ciphertext = self._read_keyring_ciphertext()
            if not ciphertext:
                entries = {}
            else:
                token = base64.b64decode(ciphertext)
                entries = self._decrypt_entries(token)
        type(self)._shared_master_key = master_key
        type(self)._shared_salt = salt
        type(self)._shared_cache = entries
        return entries

    # ------------------------------------------------------------------
    def _persist_entries(self, entries: Dict[str, Dict[str, str]]) -> None:
        self._ensure_master_key()
        salt = self._ensure_salt()
        token = self._encrypt_entries(entries)
        if self.backend == "fernet":
            self.VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": 1,
                "salt": base64.b64encode(salt).decode("utf-8"),
                "ciphertext": base64.b64encode(token).decode("utf-8"),
            }
            with self.VAULT_PATH.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
        else:
            text = base64.b64encode(token).decode("utf-8")
            salt_text = base64.b64encode(salt).decode("utf-8")
            try:
                keyring.set_password(self.KEYRING_SERVICE, self.KEYRING_ENTRY, text)
                keyring.set_password(self.KEYRING_SERVICE, self.KEYRING_SALT_ENTRY, salt_text)
            except keyring.errors.KeyringError as exc:  # pragma: no cover - 依赖系统环境
                raise SecretsBackendError("写入系统 Keyring 失败。") from exc
        type(self)._shared_cache = entries

    # ------------------------------------------------------------------
    def _read_vault_file(self) -> Dict[str, str]:
        if not self.VAULT_PATH.exists():
            return {}
        try:
            payload = json.loads(self.VAULT_PATH.read_text(encoding="utf-8"))
            salt_text = payload.get("salt")
            if salt_text:
                type(self)._shared_salt = base64.b64decode(salt_text)
            return payload
        except json.JSONDecodeError as exc:  # pragma: no cover - 防御性
            raise SecretsError("密钥库文件损坏。") from exc

    # ------------------------------------------------------------------
    def _read_keyring_ciphertext(self) -> Optional[str]:
        try:
            ciphertext = keyring.get_password(self.KEYRING_SERVICE, self.KEYRING_ENTRY)
            salt_text = keyring.get_password(self.KEYRING_SERVICE, self.KEYRING_SALT_ENTRY)
        except keyring.errors.KeyringError as exc:  # pragma: no cover - 依赖系统环境
            raise SecretsBackendError("读取系统 Keyring 失败。") from exc
        if salt_text:
            type(self)._shared_salt = base64.b64decode(salt_text)
        return ciphertext

    # ------------------------------------------------------------------
    def _load_or_create_salt(self) -> bytes:
        if self.backend == "fernet":
            payload = self._read_vault_file()
            salt_text = payload.get("salt")
            if salt_text:
                return base64.b64decode(salt_text)
            return os.urandom(16)
        _ = self._read_keyring_ciphertext()
        if self._shared_salt is not None:
            return self._shared_salt
        salt = os.urandom(16)
        salt_text = base64.b64encode(salt).decode("utf-8")
        try:
            keyring.set_password(self.KEYRING_SERVICE, self.KEYRING_SALT_ENTRY, salt_text)
        except keyring.errors.KeyringError as exc:  # pragma: no cover - 依赖系统环境
            raise SecretsBackendError("写入系统 Keyring 失败。") from exc
        return salt

    # ------------------------------------------------------------------
    def _ensure_master_key(self) -> bytes:
        master_key = type(self)._shared_master_key
        if master_key is None:
            raise SecretsLockedError("请先设置主密码。")
        return master_key

    # ------------------------------------------------------------------
    def _ensure_salt(self) -> bytes:
        salt = type(self)._shared_salt
        if salt is not None:
            return salt
        salt = self._load_or_create_salt()
        type(self)._shared_salt = salt
        return salt

    # ------------------------------------------------------------------
    def _encrypt_entries(self, entries: Dict[str, Dict[str, str]]) -> bytes:
        data = json.dumps(entries, ensure_ascii=False).encode("utf-8")
        fernet = Fernet(self._ensure_master_key())
        return fernet.encrypt(data)

    # ------------------------------------------------------------------
    def _decrypt_entries(self, token: bytes) -> Dict[str, Dict[str, str]]:
        fernet = Fernet(self._ensure_master_key())
        try:
            data = fernet.decrypt(token)
        except InvalidToken as exc:
            raise SecretsError("主密码错误或密钥库被篡改。") from exc
        try:
            return json.loads(data.decode("utf-8"))
        except json.JSONDecodeError as exc:  # pragma: no cover - 防御性
            raise SecretsError("密钥库内容损坏。") from exc

    # ------------------------------------------------------------------
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=390000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


__all__ = [
    "SecretsService",
    "SecretsError",
    "SecretsExpiredError",
    "SecretsLockedError",
    "SecretsNotFoundError",
    "SecretsBackendError",
]
