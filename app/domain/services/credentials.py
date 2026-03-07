from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet

from app.config.settings import AppSettings


class CredentialCipher:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self._fernet = Fernet(self._load_key())

    def _load_key(self) -> bytes:
        if self.settings.secret_key:
            return self.settings.secret_key.encode("utf-8")
        key_path = self.settings.secret_key_path
        key_path.parent.mkdir(parents=True, exist_ok=True)
        if key_path.exists():
            return key_path.read_bytes().strip()
        key = base64.urlsafe_b64encode(os.urandom(32))
        key_path.write_bytes(key)
        return key

    def encrypt(self, value: str) -> str:
        if not value:
            return ""
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str) -> str:
        if not value:
            return ""
        return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")
