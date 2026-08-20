#!/usr/bin/env python3
"""Authenticated, bounded alert normalization without automatic execution."""

import hashlib
import ipaddress
import json
import re
import threading
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml


class WebhookAlertListener:
    """Convert accepted monitoring events into structured policy-review requests."""

    _EVENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    _HOSTNAME = re.compile(
        r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*$"
    )

    def __init__(
        self,
        base_dir: Path | None = None,
        *,
        ingestion_enabled: bool | None = None,
    ):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.policy = self._load_policy()
        configured_enabled = bool(self.policy.get("enabled", False))
        self.ingestion_enabled = (
            configured_enabled if ingestion_enabled is None else ingestion_enabled
        )
        self._seen_event_ids: set[str] = set()
        self._event_order: deque[str] = deque()
        self._lock = threading.Lock()

    def _load_policy(self) -> dict[str, Any]:
        policy_path = self.base_dir / "config" / "automation_policy.yaml"
        if not policy_path.exists():
            return {"enabled": False}
        with policy_path.open("r", encoding="utf-8") as policy_file:
            policy = yaml.safe_load(policy_file) or {}
        return policy if isinstance(policy, dict) else {"enabled": False}

    @staticmethod
    def _reject(status: str, reason: str) -> dict[str, Any]:
        return {
            "status": status,
            "accepted": False,
            "reason": reason,
            "investigation_request": None,
            "next_action": "NONE",
        }

    @classmethod
    def _valid_target(cls, target: str) -> bool:
        try:
            ipaddress.ip_address(target)
            return True
        except ValueError:
            return bool(cls._HOSTNAME.fullmatch(target))

    @staticmethod
    def _clean_text(value: Any, *, maximum_length: int) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = " ".join(value.split())
        if not cleaned or len(cleaned) > maximum_length:
            return None
        if any(ord(character) < 32 for character in value if character not in "\t\r\n"):
            return None
        return cleaned

    def _remember_event(self, event_id: str) -> bool:
        max_seen_events = int(self.policy.get("max_seen_events", 10000))
        max_seen_events = min(max(max_seen_events, 1), 100000)
        with self._lock:
            if event_id in self._seen_event_ids:
                return False
            self._seen_event_ids.add(event_id)
            self._event_order.append(event_id)
            while len(self._event_order) > max_seen_events:
                expired = self._event_order.popleft()
                self._seen_event_ids.discard(expired)
        return True

    def process_alert_payload(
        self,
        alert_payload: Any,
        *,
        authenticated: bool = False,
        authentication_reference: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Validate one alert and return a non-executing investigation request."""
        if not self.ingestion_enabled:
            return self._reject(
                "INGESTION_DISABLED",
                "Alert ingestion is disabled until the approved authentication gateway is configured.",
            )
        cleaned_authentication_reference = self._clean_text(
            authentication_reference, maximum_length=128
        )
        if (
            not authenticated
            or not cleaned_authentication_reference
            or not self._EVENT_ID.fullmatch(cleaned_authentication_reference)
        ):
            return self._reject(
                "UNAUTHENTICATED",
                "A verified authentication reference is required.",
            )
        if not isinstance(alert_payload, dict):
            return self._reject("INVALID_PAYLOAD", "Alert payload must be a JSON object.")
        try:
            payload_size = len(json.dumps(alert_payload, ensure_ascii=False).encode("utf-8"))
        except (TypeError, ValueError):
            return self._reject("INVALID_PAYLOAD", "Alert payload is not JSON serializable.")
        maximum_payload_bytes = int(self.policy.get("max_payload_bytes", 8192))
        if payload_size > maximum_payload_bytes:
            return self._reject("PAYLOAD_TOO_LARGE", "Alert payload exceeds the configured size limit.")

        required_fields = ("event_id", "source", "alert_name", "host", "severity", "occurred_at")
        missing_fields = [field for field in required_fields if not alert_payload.get(field)]
        if missing_fields:
            return self._reject(
                "INVALID_PAYLOAD", "Missing required fields: " + ", ".join(missing_fields) + "."
            )
        event_id = self._clean_text(alert_payload["event_id"], maximum_length=128)
        source = self._clean_text(alert_payload["source"], maximum_length=64)
        alert_name = self._clean_text(alert_payload["alert_name"], maximum_length=200)
        host = self._clean_text(alert_payload["host"], maximum_length=253)
        severity = self._clean_text(alert_payload["severity"], maximum_length=16)
        if not all((event_id, source, alert_name, host, severity)):
            return self._reject("INVALID_PAYLOAD", "One or more alert fields are invalid.")
        if not self._EVENT_ID.fullmatch(event_id):
            return self._reject("INVALID_PAYLOAD", "event_id has an invalid format.")
        if not self._valid_target(host):
            return self._reject("INVALID_TARGET", "Alert host must be a valid IP address or hostname.")

        normalized_source = source.casefold()
        allowed_sources = {
            str(item).casefold() for item in self.policy.get("allowed_sources", [])
        }
        if allowed_sources and normalized_source not in allowed_sources:
            return self._reject("SOURCE_NOT_ALLOWED", "Alert source is not allowed by policy.")
        normalized_severity = severity.upper()
        allowed_severities = {
            str(item).upper()
            for item in self.policy.get(
                "allowed_severities", ["INFO", "WARNING", "HIGH", "CRITICAL"]
            )
        }
        if normalized_severity not in allowed_severities:
            return self._reject("INVALID_SEVERITY", "Alert severity is not recognized.")

        try:
            occurred_at = datetime.fromisoformat(
                str(alert_payload["occurred_at"]).replace("Z", "+00:00")
            )
        except ValueError:
            return self._reject("INVALID_TIMESTAMP", "occurred_at is not an ISO-8601 timestamp.")
        if occurred_at.tzinfo is None:
            return self._reject("INVALID_TIMESTAMP", "occurred_at must include a timezone.")
        reference_time = now or datetime.now(timezone.utc)
        if reference_time.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        occurred_utc = occurred_at.astimezone(timezone.utc)
        reference_utc = reference_time.astimezone(timezone.utc)
        freshness_seconds = int(self.policy.get("freshness_seconds", 300))
        future_tolerance_seconds = int(self.policy.get("future_tolerance_seconds", 30))
        if occurred_utc < reference_utc - timedelta(seconds=freshness_seconds):
            return self._reject("STALE_EVENT", "Alert timestamp is outside the freshness window.")
        if occurred_utc > reference_utc + timedelta(seconds=future_tolerance_seconds):
            return self._reject("FUTURE_EVENT", "Alert timestamp is too far in the future.")
        if not self._remember_event(event_id):
            return self._reject("DUPLICATE_EVENT", "Alert event_id has already been accepted.")

        fingerprint_source = json.dumps(
            {
                "event_id": event_id,
                "source": normalized_source,
                "host": host.casefold(),
                "alert_name": alert_name,
                "occurred_at": occurred_utc.isoformat(),
            },
            sort_keys=True,
        )
        event_fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()
        investigation_request = {
            "request_id": f"alert-{event_fingerprint[:12]}",
            "request_type": "MONITORING_ALERT_REVIEW",
            "event_id": event_id,
            "source": normalized_source,
            "alert_name": alert_name,
            "target": host,
            "severity": normalized_severity,
            "occurred_at": occurred_utc.isoformat(),
            "authentication_reference": cleaned_authentication_reference,
            "event_fingerprint": event_fingerprint,
            "constraints": {
                "read_only": True,
                "automatic_execution_allowed": False,
                "automatic_remediation_allowed": False,
                "requires_entity_resolution": True,
                "requires_policy_evaluation": True,
            },
        }
        return {
            "status": "ACCEPTED_FOR_POLICY_REVIEW",
            "accepted": True,
            "reason": "Alert was normalized; no investigation or action was executed.",
            "investigation_request": investigation_request,
            "next_action": "POLICY_REVIEW_REQUIRED",
        }


if __name__ == "__main__":
    print(WebhookAlertListener().process_alert_payload({})["status"])
