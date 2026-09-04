"""Local-only CSRF and replay boundary for the P10 HTTP presentation surface."""

from __future__ import annotations

import secrets
import threading
import urllib.parse
from typing import Any

from core.execution.p10_engine import P10ExecutionEngine, P10SafetyError


class P10LocalAPIContext:
    def __init__(self, engine: P10ExecutionEngine):
        self.engine = engine
        self.csrf_token = secrets.token_urlsafe(32)
        self._nonces: set[str] = set()
        self._lock = threading.Lock()

    @staticmethod
    def is_local(client_host: str) -> bool:
        return client_host in {"127.0.0.1", "::1", "localhost"} or client_host.startswith("127.")

    @classmethod
    def is_same_origin_loopback(cls, host_header: Any, origin_header: Any) -> bool:
        if not isinstance(host_header, str) or not host_header:
            return False
        host_text = host_header.strip()
        if host_text.startswith("["):
            hostname = host_text[1:host_text.find("]")]
        else:
            hostname = host_text.split(":", 1)[0]
        if not cls.is_local(hostname):
            return False
        if origin_header in (None, ""):
            return True
        try:
            origin_host = urllib.parse.urlparse(str(origin_header)).hostname or ""
        except ValueError:
            return False
        return cls.is_local(origin_host)

    def session_metadata(self) -> dict[str, Any]:
        return {
            "phase": "P10",
            "mode": "OWNER_FULL_CONTROL",
            "approval_state": "OWNER_CONTROLLED",
            "owner_reference": "MNE-BRAIN-OWNER",
            "csrf_token": self.csrf_token,
            "audit_mode": "IN_MEMORY_ONLY",
            "retention": "NONE",
            "execution_enabled": self.engine.execution_enabled,
            "local_interface_only": True,
            "one_approval_covers_prechecks_change_postchecks_and_declared_rollback": True,
        }

    def authorize_mutation(self, *, client_host: str, csrf_token: Any, nonce: Any, host_header: Any = "localhost", origin_header: Any = None) -> None:
        if not self.is_local(client_host):
            raise P10SafetyError("P10 write endpoints are local-interface-only.")
        if not self.is_same_origin_loopback(host_header, origin_header):
            raise P10SafetyError("P10 same-origin loopback validation failed.")
        if not isinstance(csrf_token, str) or not secrets.compare_digest(csrf_token, self.csrf_token):
            raise P10SafetyError("P10 CSRF validation failed.")
        if not isinstance(nonce, str) or not 16 <= len(nonce) <= 128 or not nonce.replace("-", "").replace("_", "").isalnum():
            raise P10SafetyError("A valid one-time request nonce is required.")
        with self._lock:
            if nonce in self._nonces:
                raise P10SafetyError("P10 request replay rejected.")
            self._nonces.add(nonce)
