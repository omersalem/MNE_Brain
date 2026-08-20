"""Resolve opaque credential key mappings without exposing secret values."""

import re
from pathlib import Path


class CredentialResolver:
    """Read an ignored environment file and return values only to a transport."""

    KEY = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir).resolve()
        self.local = self._read_env(self.base_dir / ".env")

    @staticmethod
    def _read_env(path: Path) -> dict[str, str]:
        if not path.is_file():
            return {}
        values: dict[str, str] = {}
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            values[key.strip()] = value
        return values

    def external_source(self, source_path_env: str = "MNE_FORTIGATE_CREDENTIAL_ENV_FILE") -> dict[str, str]:
        if not self.KEY.fullmatch(source_path_env):
            return {}
        raw_path = self.local.get(source_path_env, "")
        path = Path(raw_path)
        if not path.is_absolute() or not path.is_file():
            return {}
        return self._read_env(path)

    def value(self, key: str) -> str:
        """Resolve a non-secret or secret transport value with local overrides."""
        if not self.KEY.fullmatch(key):
            return ""
        if self.local.get(key):
            return self.local[key]
        return self.external_source().get(key, "")

    def resolve(self, *, target: str, host_key: str, username_key: str, password_key: str) -> tuple[str, str]:
        if not all(self.KEY.fullmatch(item) for item in (host_key, username_key, password_key)):
            raise ValueError("Credential key mapping is invalid.")
        source = self.external_source()
        if source.get(host_key) != target:
            raise ValueError("Credential target does not match the exact transport target.")
        username, password = source.get(username_key, ""), source.get(password_key, "")
        if not username or not password:
            raise ValueError("Credential values are unavailable.")
        return username, password

    def resolve_pair(self, *, username_key: str, password_key: str) -> tuple[str, str]:
        """Resolve credentials when Kerberos or a TLS pin supplies target identity."""
        if not all(self.KEY.fullmatch(item) for item in (username_key, password_key)):
            raise ValueError("Credential key mapping is invalid.")
        source = self.external_source()
        username, password = source.get(username_key, ""), source.get(password_key, "")
        if not username or not password:
            raise ValueError("Credential values are unavailable.")
        return username, password

    def readiness(self, mappings: list[dict[str, str]]) -> dict[str, bool]:
        """Return only configured/not-configured flags; never values."""
        source = self.external_source()
        return {
            str(item["id"]): all(bool(source.get(item.get(key, ""))) for key in ("host_key", "username_key", "password_key"))
            for item in mappings
        }
