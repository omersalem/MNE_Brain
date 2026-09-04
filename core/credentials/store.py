"""Credential storage that never serializes provider secrets to tracked JSON."""

from __future__ import annotations

import os
import re
from pathlib import Path
from threading import RLock
from typing import Any


class CredentialStoreError(ValueError):
    pass


class CredentialStore:
    """Prefer OS keyring, then environment and an ignored local `.env` file."""

    _REF = re.compile(r"^[A-Z][A-Z0-9_]{2,80}$")
    _SERVICE = "MNE_Brain_v2"

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()
        self.env_file = self.base_dir / ".env"
        self._lock = RLock()
        self._keyring: Any | None = None
        try:
            import keyring  # type: ignore

            self._keyring = keyring
        except Exception:
            self._keyring = None
        self._load_env_fallback()

    def _validate_ref(self, credential_ref: str) -> str:
        if not isinstance(credential_ref, str) or not self._REF.fullmatch(credential_ref):
            raise CredentialStoreError("Credential reference must be an uppercase reference name.")
        return credential_ref

    def _load_env_fallback(self) -> None:
        if not self.env_file.is_file():
            return
        try:
            for raw in self.env_file.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                if self._REF.fullmatch(key) and key not in os.environ:
                    os.environ[key] = value.strip().strip('"').strip("'")
        except OSError:
            return

    def get(self, credential_ref: str) -> str | None:
        ref = self._validate_ref(credential_ref)
        if self._keyring is not None:
            try:
                value = self._keyring.get_password(self._SERVICE, ref)
                if value:
                    return value
            except Exception:
                pass
        return os.environ.get(ref) or None

    def set(self, credential_ref: str, value: str) -> str:
        ref = self._validate_ref(credential_ref)
        if not isinstance(value, str) or not value or value != value.strip() or len(value) > 16384 or "\x00" in value or "\n" in value or "\r" in value:
            raise CredentialStoreError("Credential value is invalid.")
        with self._lock:
            if self._keyring is not None:
                try:
                    self._keyring.set_password(self._SERVICE, ref, value)
                    os.environ[ref] = value
                    return "WINDOWS_KEYRING"
                except Exception:
                    pass
            self._write_env_reference(ref, value)
            os.environ[ref] = value
            return "IGNORED_DOTENV"

    def _write_env_reference(self, ref: str, value: str) -> None:
        existing: dict[str, str] = {}
        comments: list[str] = []
        if self.env_file.is_file():
            for raw in self.env_file.read_text(encoding="utf-8").splitlines():
                if raw.strip().startswith("#") or "=" not in raw:
                    comments.append(raw)
                else:
                    key, old = raw.split("=", 1)
                    if self._REF.fullmatch(key.strip()):
                        existing[key.strip()] = old
        existing[ref] = value
        lines = [line for line in comments if line.strip()]
        lines.extend(f"{key}={existing[key]}" for key in sorted(existing))
        temp = self.env_file.with_suffix(".env.tmp")
        temp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(temp, self.env_file)

    def status(self, credential_ref: str) -> dict[str, str]:
        ref = self._validate_ref(credential_ref)
        return {"credential_ref": ref, "status": "CONFIGURED" if self.get(ref) else "MISSING"}

    def delete(self, credential_ref: str) -> None:
        ref = self._validate_ref(credential_ref)
        with self._lock:
            if self._keyring is not None:
                try:
                    self._keyring.delete_password(self._SERVICE, ref)
                except Exception:
                    pass
            os.environ.pop(ref, None)
            if self.env_file.is_file():
                kept = [line for line in self.env_file.read_text(encoding="utf-8").splitlines() if not line.startswith(ref + "=")]
                self.env_file.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
