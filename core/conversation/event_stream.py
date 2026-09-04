"""Canonical in-memory event log with reconnect-safe event IDs."""

from __future__ import annotations

import json
import secrets
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema


class EventStream:
    def __init__(self, base_dir: Path):
        self._events: dict[str, list[dict[str, Any]]] = {}
        self._conditions: dict[str, threading.Condition] = {}
        self._lock = threading.RLock()
        self._schema = json.loads((base_dir / "00_meta/schemas/stream-event.schema.json").read_text(encoding="utf-8"))

    def append(self, *, thread_id: str, turn_id: str, provider_id: str, event_type: str, status: str, redacted_payload: dict[str, Any]) -> dict[str, Any]:
        event = {
            "event_id": "evt_" + secrets.token_urlsafe(18),
            "thread_id": thread_id,
            "turn_id": turn_id,
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider_id": provider_id,
            "status": status,
            "redacted_payload": deepcopy(redacted_payload),
        }
        jsonschema.Draft7Validator(self._schema, format_checker=jsonschema.FormatChecker()).validate(event)
        with self._lock:
            self._events.setdefault(turn_id, []).append(event)
            condition = self._conditions.setdefault(turn_id, threading.Condition(self._lock))
            condition.notify_all()
        return deepcopy(event)

    def list_after(self, turn_id: str, last_event_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            items = self._events.get(turn_id, [])
            if not last_event_id:
                return deepcopy(items)
            for index, event in enumerate(items):
                if event["event_id"] == last_event_id:
                    return deepcopy(items[index + 1:])
            return deepcopy(items)

    def wait_after(self, turn_id: str, last_event_id: str | None, timeout: float = 15.0) -> list[dict[str, Any]]:
        with self._lock:
            existing = self.list_after(turn_id, last_event_id)
            if existing:
                return existing
            condition = self._conditions.setdefault(turn_id, threading.Condition(self._lock))
            condition.wait(timeout=max(0.0, min(timeout, 30.0)))
            return self.list_after(turn_id, last_event_id)

    @staticmethod
    def encode_sse(event: dict[str, Any]) -> bytes:
        payload = json.dumps(event, separators=(",", ":"), ensure_ascii=False)
        return f"id: {event['event_id']}\nevent: {event['event_type']}\ndata: {payload}\n\n".encode("utf-8")

