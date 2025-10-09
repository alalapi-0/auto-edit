"""本地加密工具，提供 Fernet 对称加密封装。"""
from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


class EncryptionError(Exception):
    """加解密相关的通用异常。"""


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """从密码与盐推导出 Fernet key。"""

    if len(salt) != 16:
        raise ValueError("盐值必须是 16 字节")
    # 简化实现：使用 SHA256 派生，避免额外依赖。
    import hashlib

    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 390000)
    return base64.urlsafe_b64encode(digest)


def generate_salt() -> bytes:
    """生成随机盐值。"""

    return os.urandom(16)


def encrypt_text(text: str, password: str, *, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """加密文本，返回 (盐值, 密文)。"""

    if salt is None:
        salt = generate_salt()
    key = derive_key_from_password(password, salt)
    token = Fernet(key).encrypt(text.encode("utf-8"))
    return salt, token


def decrypt_text(token: bytes, password: str, *, salt: bytes) -> str:
    """解密文本。"""

    key = derive_key_from_password(password, salt)
    try:
        return Fernet(key).decrypt(token).decode("utf-8")
    except InvalidToken as exc:  # pragma: no cover - 需运行时验证
        raise EncryptionError("解密失败，请检查主密码是否正确") from exc


def save_encrypted_file(path: Path | str, data: bytes) -> None:
    """保存加密后的文件。"""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(data)


def load_encrypted_file(path: Path | str) -> bytes:
    """读取加密文件内容。"""

    path = Path(path)
    with path.open("rb") as handle:
        return handle.read()


__all__ = [
    "EncryptionError",
    "derive_key_from_password",
    "generate_salt",
    "encrypt_text",
    "decrypt_text",
    "save_encrypted_file",
    "load_encrypted_file",
]
