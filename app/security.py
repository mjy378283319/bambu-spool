"""本地加密：仅用于把拓竹账号密码落库时做加密。

密钥文件自动生成在数据目录下，权限 0600。删掉密钥文件意味着需要重新登录。
"""
from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken

from .config import settings


def _load_key() -> bytes:
    path = settings.secret_key_path
    if not path.exists():
        path.write_bytes(Fernet.generate_key())
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    return path.read_bytes().strip()


def encrypt(plain: str) -> str:
    if not plain:
        return ""
    return _load_key() and Fernet(_load_key()).encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt(token: str) -> str:
    if not token:
        return ""
    try:
        return Fernet(_load_key()).decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        # 密钥换过或数据损坏，按未保存处理
        return ""
