#!/usr/bin/env python3
"""Fail-closed sole-owner execution state machine with in-memory audit data."""

import json
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


class ExecutionEngine:
    """Coordinate an owner-instructed driver callback without owning protocol logic.

    Execution is disabled by default. The engine never auto-runs rollback and
    never stores commands, raw output, credentials, or exception text in audit
    records.
    """

    _audit_lock = threading.Lock()
    _WRITE_TOKENS = re.compile(
        r"\b(?:set|configure|config|delete|remove|reboot|restart|clear|shutdown|format|write)\b",
        re.IGNORECASE,
    )
    _TRANSIENT_STATUSES = {"TRANSIENT_FAILURE", "TIMEOUT", "NETWORK_UNREACHABLE"}

    def __init__(
        self,
        base_dir: Path | None = None,
        max_retries: int = 2,
        timeout_seconds: int = 10,
        *,
        execution_enabled: bool = False,
        backoff_base_seconds: float = 0.25,
    ):
        if isinstance(max_retries, bool) or not isinstance(max_retries, int) or not 0 <= max_retries <= 5:
            raise ValueError("max_retries must be an integer from 0 through 5")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if backoff_base_seconds < 0:
            raise ValueError("backoff_base_seconds cannot be negative")
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.execution_enabled = execution_enabled
        self.backoff_base_seconds = backoff_base_seconds
        self.audit_log_file = self.base_dir / "operations" / "actions" / "audit_log.jsonl"
        self.audit_records: list[dict[str, Any]] = []

    @classmethod
    def _validate_action(cls, action_data: Any) -> tuple[dict[str, Any] | None, str | None]:
        if not isinstance(action_data, dict):
            return None, "ACTION_NOT_A_MAPPING"
        action_id = action_data.get("action_id")
        platform = action_data.get("platform")
        command = action_data.get("command")
        risk_level = action_data.get("risk_level")
        if not isinstance(action_id, str) or not action_id:
            return None, "ACTION_ID_MISSING"
        if not isinstance(platform, str) or not platform:
            return None, "PLATFORM_MISSING"
        if not isinstance(command, str) or not command.strip():
            return None, "COMMAND_MISSING"
        if isinstance(risk_level, bool) or not isinstance(risk_level, int) or risk_level not in range(5):
            return None, "INVALID_RISK_LEVEL"
        if risk_level == 0 and cls._WRITE_TOKENS.search(command):
            return None, "READ_ONLY_ACTION_CONTAINS_WRITE_TOKEN"
        for check_field in ("pre_checks", "post_checks"):
            checks = action_data.get(check_field, [])
            if not isinstance(checks, list) or not all(
                isinstance(check, str) and check for check in checks
            ):
                return None, f"INVALID_{check_field.upper()}"
        return {
            "action_id": action_id,
            "platform": platform,
            "command": command.strip(),
            "risk_level": risk_level,
            "rollback_available": bool(
                isinstance(action_data.get("rollback_command"), str)
                and action_data.get("rollback_command", "").strip().casefold() not in {"", "none"}
            ),
        }, None

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _base_result(
        self,
        *,
        action_id: str,
        risk_level: int | None,
        execution_id: str,
        correlation_id: str,
        status: str,
        attempts: int = 0,
        driver_status: str | None = None,
        error_code: str | None = None,
        rollback_available: bool = False,
        duration_seconds: float = 0.0,
    ) -> dict[str, Any]:
        return {
            "execution_id": execution_id,
            "correlation_id": correlation_id,
            "action_id": action_id,
            "status": status,
            "success": status == "SUCCESS",
            "attempts": attempts,
            "duration_seconds": round(duration_seconds, 4),
            "risk_level": risk_level,
            "driver_status": driver_status,
            "error_code": error_code,
            "rollback_available": rollback_available,
            "rollback_status": (
                "PLANNED_REQUIRES_EXPLICIT_OWNER_INSTRUCTION"
                if rollback_available and attempts > 0 and status in {"FAILED", "TIMEOUT"}
                else "NOT_REQUIRED"
            ),
            "timestamp": self._timestamp(),
            "audit_persisted": False,
        }

    def execute_action(
        self,
        action_data: dict[str, Any],
        driver_func: Callable[[str, str], dict[str, Any]],
        *,
        owner_reference: str | None = None,
        explicit_owner_instruction: bool = False,
        cancellation_event: threading.Event | None = None,
        correlation_id: str | None = None,
        persist_audit: bool = False,
    ) -> dict[str, Any]:
        """Run an injected driver only after every execution boundary passes."""
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        correlation = correlation_id or f"corr-{uuid.uuid4().hex[:12]}"
        persistence_allowed = (
            persist_audit is True
            and owner_reference == "MNE-BRAIN-OWNER"
            and explicit_owner_instruction is True
        )
        validated_action, validation_error = self._validate_action(action_data)
        if validated_action is None:
            result = self._base_result(
                action_id=str(action_data.get("action_id", "unknown")) if isinstance(action_data, dict) else "unknown",
                risk_level=action_data.get("risk_level") if isinstance(action_data, dict) else None,
                execution_id=execution_id,
                correlation_id=correlation,
                status="INVALID_ACTION",
                error_code=validation_error,
            )
            return self._record_audit(result, persistence_allowed)

        action_id = validated_action["action_id"]
        risk_level = validated_action["risk_level"]
        rollback_available = validated_action["rollback_available"]
        if risk_level == 4:
            result = self._base_result(
                action_id=action_id,
                risk_level=risk_level,
                execution_id=execution_id,
                correlation_id=correlation,
                status="CRITICAL_EXCEPTION_REQUIRED",
                error_code="P10_CRITICAL_EXCEPTION_ONLY",
                rollback_available=rollback_available,
            )
            return self._record_audit(result, persistence_allowed)
        if not self.execution_enabled:
            result = self._base_result(
                action_id=action_id,
                risk_level=risk_level,
                execution_id=execution_id,
                correlation_id=correlation,
                status="EXECUTION_DISABLED",
                error_code="ENGINE_DISABLED",
                rollback_available=rollback_available,
            )
            return self._record_audit(result, persistence_allowed)
        if (
            owner_reference != "MNE-BRAIN-OWNER"
            or explicit_owner_instruction is not True
        ):
            result = self._base_result(
                action_id=action_id,
                risk_level=risk_level,
                execution_id=execution_id,
                correlation_id=correlation,
                status="NOT_AUTHORIZED",
                error_code="EXPLICIT_OWNER_INSTRUCTION_REQUIRED",
                rollback_available=rollback_available,
            )
            return self._record_audit(result, persistence_allowed)
        if cancellation_event is not None and cancellation_event.is_set():
            result = self._base_result(
                action_id=action_id,
                risk_level=risk_level,
                execution_id=execution_id,
                correlation_id=correlation,
                status="CANCELLED",
                error_code="CANCELLED_BEFORE_EXECUTION",
                rollback_available=rollback_available,
            )
            return self._record_audit(result, persistence_allowed)

        maximum_attempts = 1 + (self.max_retries if risk_level == 0 else 0)
        attempts = 0
        driver_status: str | None = None
        started_at = time.monotonic()
        while attempts < maximum_attempts:
            if cancellation_event is not None and cancellation_event.is_set():
                result = self._base_result(
                    action_id=action_id,
                    risk_level=risk_level,
                    execution_id=execution_id,
                    correlation_id=correlation,
                    status="CANCELLED",
                    attempts=attempts,
                    driver_status=driver_status,
                    error_code="CANCELLED_BEFORE_RETRY",
                    rollback_available=rollback_available,
                    duration_seconds=time.monotonic() - started_at,
                )
                return self._record_audit(result, persistence_allowed)

            attempts += 1
            try:
                driver_result = driver_func(validated_action["platform"], validated_action["command"])
                if not isinstance(driver_result, dict):
                    driver_status = "INVALID_DRIVER_RESULT"
                else:
                    driver_status = str(driver_result.get("status", "INVALID_DRIVER_RESULT")).upper()
            except Exception:
                driver_status = "DRIVER_EXCEPTION"

            if driver_status == "SUCCESS":
                result = self._base_result(
                    action_id=action_id,
                    risk_level=risk_level,
                    execution_id=execution_id,
                    correlation_id=correlation,
                    status="SUCCESS",
                    attempts=attempts,
                    driver_status=driver_status,
                    rollback_available=rollback_available,
                    duration_seconds=time.monotonic() - started_at,
                )
                return self._record_audit(result, persistence_allowed)
            if driver_status not in self._TRANSIENT_STATUSES or attempts >= maximum_attempts:
                break
            if self.backoff_base_seconds:
                time.sleep(self.backoff_base_seconds * (2 ** (attempts - 1)))

        final_status = "TIMEOUT" if driver_status == "TIMEOUT" else "FAILED"
        result = self._base_result(
            action_id=action_id,
            risk_level=risk_level,
            execution_id=execution_id,
            correlation_id=correlation,
            status=final_status,
            attempts=attempts,
            driver_status=driver_status,
            error_code=driver_status or "DRIVER_FAILED",
            rollback_available=rollback_available,
            duration_seconds=time.monotonic() - started_at,
        )
        return self._record_audit(result, persistence_allowed)

    def _record_audit(self, result: dict[str, Any], persist: bool) -> dict[str, Any]:
        """Record only bounded metadata; commands and driver output are excluded."""
        audit_record = dict(result)
        audit_record["audit_persisted"] = persist
        self.audit_records.append(audit_record)
        if persist:
            self.audit_log_file.parent.mkdir(parents=True, exist_ok=True)
            serialized = json.dumps(audit_record, sort_keys=True)
            with self._audit_lock:
                with self.audit_log_file.open("a", encoding="utf-8") as audit_file:
                    audit_file.write(serialized + "\n")
        return audit_record


if __name__ == "__main__":
    engine = ExecutionEngine()
    result = engine.execute_action(
        {
            "action_id": "example-read",
            "platform": "example",
            "command": "show status",
            "risk_level": 0,
            "pre_checks": [],
            "post_checks": [],
        },
        lambda _platform, _command: {"status": "SUCCESS"},
    )
    print(result["status"])
