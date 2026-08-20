#!/usr/bin/env python3
"""Fail-closed read-only transport boundary and evidence normalization."""

import hashlib
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event
from typing import Any, Callable

import jsonschema


TransportExecutor = Callable[[dict[str, Any]], dict[str, Any]]


class ReadOnlyVerificationAdapter:
    """Execute only pre-validated checks through an injected transport.

    This module imports no network, subprocess, SSH, or vendor SDK. The
    injected transport is the future security-reviewed integration boundary.
    Fixture mode can exercise normalization but can never create accepted live
    evidence or claim that a connection was attempted.
    """

    _REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
    _CREDENTIAL_REFERENCE = re.compile(
        r"^(?:secretref|vaultref)://[A-Za-z0-9][A-Za-z0-9._/-]{2,255}$"
    )
    _SENSITIVE_ASSIGNMENT = re.compile(
        r"(?i)\b(password|passwd|token|secret|community|authorization|api[_-]?key)\b\s*[:=]\s*([^\s,;]+)"
    )
    _BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]+=*")
    _PRIVATE_KEY = re.compile(
        r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----",
        re.IGNORECASE,
    )

    def __init__(
        self,
        adapter_id: str,
        transport_executor: TransportExecutor | None = None,
        *,
        simulation_mode: bool = False,
        base_dir: Path | None = None,
    ):
        if not re.fullmatch(r"[a-z][a-z0-9_-]{2,63}", adapter_id):
            raise ValueError("adapter_id has an invalid format")
        self.adapter_id = adapter_id
        self.transport_executor = transport_executor
        self.simulation_mode = simulation_mode
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        schema_path = self.base_dir / "00_meta" / "schemas" / "live-evidence.schema.json"
        self.live_evidence_schema = json.loads(schema_path.read_text(encoding="utf-8"))

    @classmethod
    def _redact_output(cls, output: str) -> str:
        cleaned = "".join(
            character if character in "\n\r\t" or ord(character) >= 32 else "?"
            for character in output
        )
        cleaned = cls._PRIVATE_KEY.sub("[REDACTED_PRIVATE_KEY]", cleaned)
        cleaned = cls._BEARER.sub("Bearer [REDACTED]", cleaned)
        return cls._SENSITIVE_ASSIGNMENT.sub(lambda match: f"{match.group(1)}=[REDACTED]", cleaned).strip()

    @staticmethod
    def _fingerprint(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _evidence_record(
        self,
        *,
        entity_id: str,
        profile_name: str,
        platform: str,
        check_id: str,
        scope_reference: str,
        content: str,
        freshness_ttl_seconds: int,
        observed_at: datetime,
    ) -> dict[str, Any]:
        observed_utc = observed_at.astimezone(timezone.utc)
        expires_at = observed_utc + timedelta(seconds=freshness_ttl_seconds)
        content_hash = self._fingerprint(content)
        evidence_fingerprint = self._fingerprint(
            "|".join(
                [entity_id, profile_name, check_id, scope_reference, observed_utc.isoformat(), content_hash]
            )
        )[:16]
        evidence_id = f"ev-live-{evidence_fingerprint}"
        if self.simulation_mode:
            return {
                "evidence_id": f"sim-{evidence_fingerprint}",
                "entity_id": entity_id,
                "profile_name": profile_name,
                "platform": platform,
                "source_file": f"offline-fixture://{self.adapter_id}/{check_id}",
                "source": "offline transport fixture",
                "evidence_status": "simulated",
                "trust_level": 0,
                "observed_at": observed_utc.isoformat(),
                "expires_at": expires_at.isoformat(),
                "evidence_refs": [],
                "verification_target": entity_id,
                "verification_check_id": check_id,
                "verification_outcome": "simulated_success",
                "scope_reference": scope_reference,
                "transport_status": "SIMULATED_SUCCESS",
                "content_sha256": content_hash,
                "heading": f"Offline fixture - {profile_name} / {check_id}",
                "content": content,
            }

        record = {
            "evidence_id": evidence_id,
            "entity_id": entity_id,
            "profile_name": profile_name,
            "platform": platform,
            "source_file": f"live-adapter://{self.adapter_id}/{check_id}",
            "source": "owner-authorized read-only transport",
            "evidence_status": "live_verified",
            "trust_level": 5,
            "observed_at": observed_utc.isoformat(),
            "expires_at": expires_at.isoformat(),
            "evidence_refs": [evidence_id],
            "verification_target": entity_id,
            "verification_check_id": check_id,
            "verification_outcome": "success",
            "scope_reference": scope_reference,
            "transport_status": "SUCCESS",
            "content_sha256": content_hash,
            "heading": f"Live read-only evidence - {profile_name} / {check_id}",
            "content": content,
        }
        jsonschema.validate(
            instance=record,
            schema=self.live_evidence_schema,
            format_checker=jsonschema.FormatChecker(),
        )
        return record

    def collect(
        self,
        *,
        profile_name: str,
        platform: str,
        entity_id: str,
        target: str,
        checks: list[dict[str, str]],
        scope_reference: str,
        credential_reference: str,
        timeout_seconds: int,
        max_output_bytes: int,
        freshness_ttl_seconds: int,
        activation_context: dict[str, Any],
        cancellation_event: Event | None = None,
    ) -> dict[str, Any]:
        started = time.monotonic()
        if not isinstance(activation_context, dict):
            return self._blocked("INVALID_ACTIVATION_CONTEXT")
        required_activation = {
            "policy_enabled": True,
            "authorization_granted": True,
            "adapter_id": self.adapter_id,
            "entity_id": entity_id,
            "scope_reference": scope_reference,
        }
        if any(
            activation_context.get(key) != value
            for key, value in required_activation.items()
        ):
            return self._blocked("ACTIVATION_CONTEXT_MISMATCH")
        if self.simulation_mode:
            if activation_context.get("activation_state") != "OFFLINE_FIXTURE_ONLY":
                return self._blocked("SIMULATION_ACTIVATION_REQUIRED")
        elif (
            activation_context.get("activation_state") != "OWNER_AUTHORIZED_LIVE_PILOT"
            or not self._REFERENCE.fullmatch(
                str(activation_context.get("p0_containment_reference", ""))
            )
            or activation_context.get("owner_reference") != "MNE-BRAIN-OWNER"
            or activation_context.get("owner_authorization") != "EXPLICIT_OWNER_PROCEED"
        ):
            return self._blocked("OWNER_PROCEED_AND_LIVE_ACTIVATION_REQUIRED")
        if not self._REFERENCE.fullmatch(scope_reference):
            return self._blocked("INVALID_SCOPE_REFERENCE")
        if not self._CREDENTIAL_REFERENCE.fullmatch(credential_reference):
            return self._blocked("INVALID_CREDENTIAL_REFERENCE")
        if not target or not entity_id or not checks:
            return self._blocked("INVALID_REQUEST")
        if self.transport_executor is None:
            return self._blocked("TRANSPORT_NOT_CONFIGURED")

        evidence_records: list[dict[str, Any]] = []
        failures: list[dict[str, str]] = []
        command_fingerprints: list[dict[str, str]] = []
        connection_attempted = False
        checks_attempted = 0

        for check in checks:
            if cancellation_event is not None and cancellation_event.is_set():
                failures.append({"check_id": check["check_id"], "status": "CANCELLED"})
                break
            checks_attempted += 1
            command = check["command"]
            command_fingerprints.append(
                {"check_id": check["check_id"], "command_fingerprint": self._fingerprint(command)}
            )
            request = {
                "adapter_id": self.adapter_id,
                "profile_name": profile_name,
                "entity_id": entity_id,
                "target": target,
                "check_id": check["check_id"],
                "command": command,
                "credential_reference": credential_reference,
                "timeout_seconds": timeout_seconds,
                "max_output_bytes": max_output_bytes,
                "simulation_mode": self.simulation_mode,
            }
            try:
                transport_result = self.transport_executor(request)
            except Exception:
                failures.append({"check_id": check["check_id"], "status": "TRANSPORT_EXCEPTION"})
                continue
            if not isinstance(transport_result, dict):
                failures.append({"check_id": check["check_id"], "status": "INVALID_TRANSPORT_RESULT"})
                continue

            result_status = str(transport_result.get("status", "INVALID_TRANSPORT_RESULT")).upper()
            attempted = transport_result.get("connection_attempted") is True
            connection_attempted = connection_attempted or attempted
            if self.simulation_mode and attempted:
                failures.append({"check_id": check["check_id"], "status": "FIXTURE_CONNECTION_CLAIM_REJECTED"})
                continue
            if not self.simulation_mode and not attempted:
                failures.append({"check_id": check["check_id"], "status": "MISSING_CONNECTION_ATTESTATION"})
                continue
            if result_status not in {"SUCCESS", "SIMULATED_SUCCESS"}:
                failures.append({"check_id": check["check_id"], "status": result_status})
                continue
            if self.simulation_mode and result_status != "SIMULATED_SUCCESS":
                failures.append({"check_id": check["check_id"], "status": "INVALID_FIXTURE_STATUS"})
                continue
            if not self.simulation_mode and result_status != "SUCCESS":
                failures.append({"check_id": check["check_id"], "status": "INVALID_LIVE_STATUS"})
                continue

            output = transport_result.get("output")
            if not isinstance(output, str) or not output.strip():
                failures.append({"check_id": check["check_id"], "status": "EMPTY_OUTPUT"})
                continue
            if len(output.encode("utf-8")) > max_output_bytes:
                failures.append({"check_id": check["check_id"], "status": "OUTPUT_TOO_LARGE"})
                continue
            redacted_output = self._redact_output(output)
            if not redacted_output:
                failures.append({"check_id": check["check_id"], "status": "EMPTY_AFTER_REDACTION"})
                continue
            evidence_records.append(
                self._evidence_record(
                    entity_id=entity_id,
                    profile_name=profile_name,
                    platform=platform,
                    check_id=check["check_id"],
                    scope_reference=scope_reference,
                    content=redacted_output,
                    freshness_ttl_seconds=freshness_ttl_seconds,
                    observed_at=datetime.now(timezone.utc),
                )
            )

        cancelled = any(item["status"] == "CANCELLED" for item in failures)
        if cancelled and not evidence_records:
            status = "CANCELLED"
            trust_level = 0
        elif self.simulation_mode:
            status = "SIMULATED_NOT_ACCEPTED" if evidence_records else "SIMULATION_FAILED"
            trust_level = 0
            connection_attempted = False
        elif evidence_records and not failures:
            status = "SUCCESS"
            trust_level = 5
        elif evidence_records:
            status = "PARTIAL"
            trust_level = 5
        elif cancelled:
            status = "CANCELLED"
            trust_level = 0
        else:
            status = "FAILED"
            trust_level = 0
        return {
            "status": status,
            "adapter_id": self.adapter_id,
            "entity_id": entity_id,
            "trust_level": trust_level,
            "checks_attempted": checks_attempted,
            "checks_succeeded": len(evidence_records),
            "evidence_records": evidence_records,
            "failures": failures,
            "command_fingerprints": command_fingerprints,
            "connection_attempted": connection_attempted,
            "simulation_mode": self.simulation_mode,
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
            "raw_output_returned": False,
            "credential_returned": False,
        }

    def _blocked(self, reason: str) -> dict[str, Any]:
        return {
            "status": "NOT_RUN",
            "adapter_id": self.adapter_id,
            "trust_level": 0,
            "checks_attempted": 0,
            "checks_succeeded": 0,
            "evidence_records": [],
            "failures": [],
            "command_fingerprints": [],
            "connection_attempted": False,
            "simulation_mode": self.simulation_mode,
            "duration_ms": 0.0,
            "raw_output_returned": False,
            "credential_returned": False,
            "reason": reason,
        }
