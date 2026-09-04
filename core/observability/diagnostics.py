"""In-memory, secret-safe diagnostics for owner-visible failure correlation."""

from __future__ import annotations

import secrets
import threading
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from core.llm.providers.base import SAFE_PROVIDER_ERRORS


class DiagnosticStore:
    """Retain bounded safe metadata only; never retain provider bodies or exceptions."""

    def __init__(self, *, max_items: int = 500):
        self.max_items = max(10, min(max_items, 5000))
        self._items: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def record(self, *, code: str, phase: str, provider_id: str, retryable: bool | None = None) -> dict[str, Any]:
        safe_code = code if code in SAFE_PROVIDER_ERRORS else "PROVIDER_UNAVAILABLE"
        message, default_retryable = SAFE_PROVIDER_ERRORS[safe_code]
        item = {
            "diagnostic_id": "diag_" + secrets.token_urlsafe(18),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "code": safe_code,
            "message": message,
            "phase": phase if phase in {"configuration", "authorization", "request", "stream", "cancellation", "tool"} else "stream",
            "provider_id": provider_id,
            "retryable": default_retryable if retryable is None else bool(retryable),
            "sensitive_details_included": False,
        }
        with self._lock:
            self._items[item["diagnostic_id"]] = item
            while len(self._items) > self.max_items:
                self._items.pop(next(iter(self._items)))
        return deepcopy(item)

    def get(self, diagnostic_id: str) -> dict[str, Any]:
        with self._lock:
            item = self._items.get(diagnostic_id)
        if item is None:
            raise KeyError("Diagnostic not found.")
        return deepcopy(item)
