#!/usr/bin/env python3
"""Shared non-connecting protocol-driver contract."""

import hashlib
import re
from typing import Any


class ProtocolDriver:
    """Plan a protocol request and report truthful non-execution states."""

    _EMBEDDED_CREDENTIALS = re.compile(r"://[^/@:\s]+:[^/@\s]+@")

    def __init__(self, protocol: str):
        self.protocol = protocol

    def plan(self, target: Any, operation: Any) -> dict[str, Any]:
        if not isinstance(target, str) or not target.strip() or len(target) > 512:
            return self._invalid("Target must be a non-empty string of at most 512 characters.")
        if "\n" in target or "\r" in target:
            return self._invalid("Target cannot contain line breaks.")
        if self._EMBEDDED_CREDENTIALS.search(target):
            return self._invalid("Credentials embedded in a target are prohibited.")
        if "?" in target:
            return self._invalid("Query strings in targets are prohibited; use a credential-safe adapter configuration.")
        if not isinstance(operation, str) or not operation.strip() or len(operation) > 4096:
            return self._invalid("Operation must be a non-empty string of at most 4096 characters.")
        operation_text = operation.strip()
        return {
            "protocol": self.protocol,
            "status": "PLANNED",
            "target": target.strip(),
            "operation_fingerprint": hashlib.sha256(operation_text.encode("utf-8")).hexdigest(),
            "operation_length": len(operation_text),
            "connection_attempted": False,
            "output": None,
            "reason": "Request validated without opening a connection.",
        }

    def execute_request(
        self, target: Any, operation: Any, *, authorized: bool = False
    ) -> dict[str, Any]:
        plan = self.plan(target, operation)
        if plan["status"] != "PLANNED":
            return plan
        if not authorized:
            return {
                **plan,
                "status": "NOT_RUN",
                "reason": "Protocol execution is not explicitly authorized.",
            }
        return {
            **plan,
            "status": "NOT_CONFIGURED",
            "reason": "No approved transport adapter is registered; no connection was attempted.",
        }

    def _invalid(self, reason: str) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
            "status": "INVALID_REQUEST",
            "connection_attempted": False,
            "output": None,
            "reason": reason,
        }
