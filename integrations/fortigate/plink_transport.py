#!/usr/bin/env python3
"""Pinned-host-key PuTTY transport for the approved FortiGate edge pilot."""

import os
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable


ProcessRunner = Callable[..., subprocess.CompletedProcess[str]]


class PinnedPlinkFortiGateTransport:
    """Execute one exact read-only FortiGate command through pinned Plink SSH."""

    ADAPTER_ID = "fortigate_ssh_readonly"
    TARGET = "172.23.70.4"
    ENTITY_ID = "fw-fortigate-edge-01"
    CREDENTIAL_REFERENCE = "secretref://local/fortigate-edge-readonly"
    APPROVED_CHECKS = {
        "system_status": "get system status",
        "interface_stats": "get system interface physical",
    }
    KEY_NAME = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")
    HOST_KEY = re.compile(r"^ssh-[A-Za-z0-9-]+\s+\d+\s+SHA256:[A-Za-z0-9+/=]+$")

    def __init__(
        self,
        *,
        base_dir: Path,
        runner: ProcessRunner = subprocess.run,
        plink_path: Path | None = None,
    ) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.runner = runner
        self.local_config = self._read_env(self.base_dir / ".env")
        configured_plink = self.local_config.get("MNE_PLINK_PATH")
        self.plink_path = Path(
            plink_path
            or configured_plink
            or r"C:\Program Files\PuTTY\plink.exe"
        )

    @staticmethod
    def _read_env(path: Path) -> dict[str, str]:
        if not path.is_file():
            return {}
        values: dict[str, str] = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            values[key.strip()] = value
        return values

    def _blocked(self, status: str, *, attempted: bool = False) -> dict[str, Any]:
        return {
            "status": status,
            "connection_attempted": attempted,
            "output": None,
            "credential_returned": False,
            "raw_error_returned": False,
        }

    def _resolve_credentials(self) -> tuple[str, str, str]:
        source_text = self.local_config.get("MNE_FORTIGATE_CREDENTIAL_ENV_FILE", "")
        source_path = Path(source_text)
        if not source_path.is_absolute() or not source_path.is_file():
            raise ValueError("Credential environment source is unavailable.")

        host_key_name = self.local_config.get("MNE_FORTIGATE_HOST_KEY", "")
        username_key = self.local_config.get("MNE_FORTIGATE_USERNAME_KEY", "")
        password_key = self.local_config.get("MNE_FORTIGATE_PASSWORD_KEY", "")
        if not all(self.KEY_NAME.fullmatch(item) for item in (host_key_name, username_key, password_key)):
            raise ValueError("Credential key mapping is invalid.")

        source = self._read_env(source_path)
        target = source.get(host_key_name, "")
        username = source.get(username_key, "")
        password = source.get(password_key, "")
        if target != self.TARGET or username != "adminread" or not password:
            raise ValueError("Credential source does not match the approved target and identity.")
        return target, username, password

    def __call__(self, request: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(request, dict):
            return self._blocked("INVALID_REQUEST")
        check_id = request.get("check_id")
        command = request.get("command")
        if (
            request.get("adapter_id") != self.ADAPTER_ID
            or request.get("profile_name") != "fortigate_edge"
            or request.get("entity_id") != self.ENTITY_ID
            or request.get("target") != self.TARGET
            or request.get("credential_reference") != self.CREDENTIAL_REFERENCE
            or check_id not in self.APPROVED_CHECKS
            or command != self.APPROVED_CHECKS.get(check_id)
            or request.get("simulation_mode") is not False
        ):
            return self._blocked("SCOPE_BLOCKED")

        host_key = self.local_config.get("MNE_FORTIGATE_SSH_HOSTKEY", "")
        if not self.HOST_KEY.fullmatch(host_key):
            return self._blocked("HOST_KEY_NOT_CONFIGURED")
        if not self.plink_path.is_file():
            return self._blocked("TRANSPORT_NOT_CONFIGURED")

        try:
            target, username, password = self._resolve_credentials()
        except (OSError, UnicodeError, ValueError):
            return self._blocked("CREDENTIAL_NOT_CONFIGURED")

        timeout_seconds = max(1, min(int(request.get("timeout_seconds", 10)), 15))
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            with TemporaryDirectory(prefix="mne-fortigate-pilot-") as temp_dir:
                password_file = Path(temp_dir) / "credential.txt"
                password_file.write_text(password + "\n", encoding="utf-8")
                try:
                    password_file.chmod(0o600)
                except OSError:
                    pass
                arguments = [
                    str(self.plink_path),
                    "-batch",
                    "-ssh",
                    "-P",
                    "22",
                    "-hostkey",
                    host_key,
                    "-l",
                    username,
                    "-pwfile",
                    str(password_file),
                    target,
                    command,
                ]
                completed = self.runner(
                    arguments,
                    check=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout_seconds,
                    creationflags=creationflags,
                )
        except subprocess.TimeoutExpired:
            return self._blocked("TIMEOUT", attempted=True)
        except OSError:
            return self._blocked("TRANSPORT_EXCEPTION", attempted=True)

        if completed.returncode != 0:
            error_text = (completed.stderr or "").casefold()
            if "host key" in error_text:
                status = "HOST_KEY_REJECTED"
            elif "access denied" in error_text or "authentication" in error_text:
                status = "AUTHENTICATION_FAILED"
            else:
                status = "TRANSPORT_FAILED"
            return self._blocked(status, attempted=True)
        if not completed.stdout.strip():
            return self._blocked("EMPTY_OUTPUT", attempted=True)
        return {
            "status": "SUCCESS",
            "connection_attempted": True,
            "output": completed.stdout,
            "credential_returned": False,
            "raw_error_returned": False,
        }
