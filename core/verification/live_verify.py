#!/usr/bin/env python3
"""Policy-gated read-only verification planning and adapter orchestration."""

import hashlib
import json
import re
from pathlib import Path
from threading import Event
from typing import Any

import jsonschema
import yaml

from core.entity.build_entity_index import EntityIndexBuilder
from core.verification.readonly_adapter import ReadOnlyVerificationAdapter

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class LiveVerificationEngine:
    """Plan verification and invoke only an explicitly registered P2 adapter.

    The repository policy is disabled by default and the default registry is
    empty. Therefore normal construction cannot contact a target or create
    live evidence. Tests may register simulation-mode adapters, whose output is
    permanently trust level 0 and cannot enter an evidence pack.
    """

    _WRITE_TOKENS = re.compile(
        r"\b(?:set|configure|delete|remove|reboot|restart|clear|shutdown|format|write|copy)\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        base_dir: Path | None = None,
        *,
        adapters: dict[str, ReadOnlyVerificationAdapter] | None = None,
    ):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.profiles_dir = self.base_dir / "profiles"
        self.adapters = dict(adapters or {})
        self.p2_policy = self._load_p2_policy()
        schema_path = self.base_dir / "00_meta" / "schemas" / "profile.schema.json"
        if not schema_path.exists():
            schema_path = PROJECT_ROOT / "00_meta" / "schemas" / "profile.schema.json"
        self.profile_schema = json.loads(schema_path.read_text(encoding="utf-8"))

    def _load_p2_policy(self) -> dict[str, Any]:
        policy_path = self.base_dir / "config" / "p2_readonly_policy.yaml"
        if not policy_path.exists():
            return {"enabled": False, "reason": "P2 read-only policy is missing."}
        policy = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
        return policy if isinstance(policy, dict) else {"enabled": False}

    def load_profile(self, profile_name: str) -> dict[str, Any]:
        if not isinstance(profile_name, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{1,63}", profile_name):
            raise ValueError("profile_name has an invalid format")
        profile_path = self.profiles_dir / f"{profile_name}.yaml"
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile {profile_name}.yaml was not found.")
        profile = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
        if not isinstance(profile, dict):
            raise ValueError(f"Profile {profile_name}.yaml must contain a mapping.")
        try:
            jsonschema.validate(instance=profile, schema=self.profile_schema)
        except jsonschema.ValidationError as exc:
            raise ValueError(f"Profile {profile_name}.yaml does not satisfy the profile contract.") from exc
        return profile

    @classmethod
    def _validate_read_only_command(cls, command: Any) -> str:
        if not isinstance(command, str) or not command.strip():
            raise ValueError("Each verification command must be a non-empty string.")
        if cls._WRITE_TOKENS.search(command):
            raise ValueError("Verification command is not read-only.")
        return command.strip()

    def _select_checks(
        self, profile: dict[str, Any], check_id: str | None
    ) -> list[dict[str, str]]:
        seen_check_ids: set[str] = set()
        selected: list[dict[str, str]] = []
        for declared_check in profile["read_commands"]:
            declared_id = declared_check["id"]
            if declared_id in seen_check_ids:
                raise ValueError("Each read command must have a unique id.")
            seen_check_ids.add(declared_id)
            if check_id and declared_id != check_id:
                continue
            selected.append(
                {
                    "check_id": declared_id,
                    "command": self._validate_read_only_command(declared_check["command"]),
                }
            )
        if check_id and not selected:
            raise ValueError(f"Profile has no check named {check_id!r}.")
        return selected

    def build_verification_plan(
        self, profile_name: str, check_id: str | None = None
    ) -> dict[str, Any]:
        """Return a redacted plan without contacting a target."""
        profile = self.load_profile(profile_name)
        selected = self._select_checks(profile, check_id)
        connection = profile["connection"]
        planned_checks = [
            {
                "check_id": check["check_id"],
                "command_fingerprint": hashlib.sha256(check["command"].encode("utf-8")).hexdigest(),
                "maximum_trust_if_successfully_collected": 5,
            }
            for check in selected
        ]
        return {
            "status": "PLANNED",
            "profile_name": profile_name,
            "platform": profile["profile"]["platform"],
            "adapter_id": connection["adapter_id"],
            "entity_id": connection["entity_ref"],
            "planned_checks": planned_checks,
            "timeout_seconds": connection["timeout_seconds"],
            "max_output_bytes": connection["max_output_bytes"],
            "persistence_enabled": False,
            "connection_attempted": False,
            "execution_permitted": False,
        }

    @staticmethod
    def _not_run(status: str, profile_name: str, reason: str) -> dict[str, Any]:
        return {
            "status": status,
            "profile_name": profile_name,
            "trust_level": 0,
            "checks_executed": 0,
            "telemetry_results": [],
            "connection_attempted": False,
            "persistence": "NOT_REQUESTED",
            "reason": reason,
        }

    def execute_live_verification(
        self,
        profile_name: str,
        check_id: str | None = None,
        *,
        authorized: bool = False,
        entity_id: str | None = None,
        scope_reference: str | None = None,
        credential_reference: str | None = None,
        cancellation_event: Event | None = None,
    ) -> dict[str, Any]:
        if not authorized:
            return self._not_run(
                "NOT_RUN", profile_name, "Live verification is not authorized by policy."
            )
        try:
            profile = self.load_profile(profile_name)
            plan = self.build_verification_plan(profile_name, check_id)
            checks = self._select_checks(profile, check_id)
        except (FileNotFoundError, ValueError, jsonschema.ValidationError) as exc:
            return self._not_run("INVALID_PROFILE", profile_name, str(exc))

        policy_reason = str(
            self.p2_policy.get(
                "reason", "P2 read-only collection is disabled by repository policy."
            )
        )
        if self.p2_policy.get("enabled") is not True:
            result = self._not_run("NOT_CONFIGURED", profile_name, policy_reason)
            result["planned_checks"] = plan["planned_checks"]
            return result

        connection = profile["connection"]
        configured_entity = connection["entity_ref"]
        requested_entity = entity_id or configured_entity
        allowed_profiles = set(self.p2_policy.get("allowed_profiles", []))
        allowed_adapters = set(self.p2_policy.get("allowed_adapters", []))
        allowed_entities = set(self.p2_policy.get("allowed_entities", []))
        allowed_checks = set(
            self.p2_policy.get("allowed_checks", {}).get(profile_name, [])
        )
        selected_check_ids = {check["check_id"] for check in checks}
        scope_valid = (
            profile_name in allowed_profiles
            and connection["adapter_id"] in allowed_adapters
            and requested_entity == configured_entity
            and requested_entity in allowed_entities
            and selected_check_ids.issubset(allowed_checks)
        )
        if not scope_valid:
            return self._not_run(
                "SCOPE_BLOCKED", profile_name, "Profile, adapter, entity, or check is outside the approved P2 scope."
            )
        if not scope_reference or not credential_reference:
            return self._not_run(
                "MISSING_AUTHORIZATION_CONTEXT",
                profile_name,
                "Scope and opaque credential references are required.",
            )

        adapter = self.adapters.get(connection["adapter_id"])
        if adapter is None:
            return self._not_run(
                "NOT_CONFIGURED", profile_name, "No approved adapter instance is registered."
            )
        if adapter.adapter_id != connection["adapter_id"]:
            return self._not_run(
                "ADAPTER_MISMATCH", profile_name, "Registered adapter identity does not match the profile."
            )

        timeout_seconds = min(
            int(connection["timeout_seconds"]),
            int(self.p2_policy.get("timeout_seconds_maximum", 15)),
        )
        max_output_bytes = min(
            int(connection["max_output_bytes"]),
            int(self.p2_policy.get("max_output_bytes_maximum", 65536)),
        )
        max_checks = int(self.p2_policy.get("maximum_checks_per_request", 1))
        if len(checks) > max_checks:
            return self._not_run(
                "BUDGET_BLOCKED", profile_name, "Requested checks exceed the approved request budget."
            )

        matches = EntityIndexBuilder(base_dir=self.base_dir).resolve_entity(requested_entity)
        if len(matches) != 1 or matches[0]["entity_id"] != requested_entity or not matches[0]["ip"]:
            return self._not_run(
                "TARGET_UNAVAILABLE", profile_name, "The scoped entity has no exact canonical management target."
            )
        freshness_ttl_seconds = min(
            int(profile["normalization"]["freshness_ttl_seconds"]),
            int(self.p2_policy.get("freshness_ttl_seconds_maximum", 900)),
        )
        adapter_result = adapter.collect(
            profile_name=profile_name,
            platform=profile["profile"]["platform"],
            entity_id=requested_entity,
            target=matches[0]["ip"],
            checks=checks,
            scope_reference=scope_reference,
            credential_reference=credential_reference,
            timeout_seconds=timeout_seconds,
            max_output_bytes=max_output_bytes,
            freshness_ttl_seconds=freshness_ttl_seconds,
            activation_context={
                "policy_enabled": True,
                "authorization_granted": True,
                "activation_state": self.p2_policy.get("activation_state"),
                "adapter_id": connection["adapter_id"],
                "entity_id": requested_entity,
                "scope_reference": scope_reference,
                "p0_containment_reference": self.p2_policy.get(
                    "p0_containment_reference"
                ),
                "owner_reference": self.p2_policy.get("owner_reference"),
                "owner_authorization": self.p2_policy.get("owner_authorization"),
            },
            cancellation_event=cancellation_event,
        )
        return {
            "status": adapter_result["status"],
            "profile_name": profile_name,
            "platform": profile["profile"]["platform"],
            "adapter_id": connection["adapter_id"],
            "entity_id": requested_entity,
            "trust_level": adapter_result["trust_level"],
            "checks_executed": adapter_result["checks_succeeded"],
            "checks_attempted": adapter_result["checks_attempted"],
            "telemetry_results": adapter_result["evidence_records"],
            "failures": adapter_result["failures"],
            "command_fingerprints": adapter_result["command_fingerprints"],
            "connection_attempted": adapter_result["connection_attempted"],
            "simulation_mode": adapter_result["simulation_mode"],
            "duration_ms": adapter_result["duration_ms"],
            "raw_output_returned": adapter_result["raw_output_returned"],
            "credential_returned": adapter_result["credential_returned"],
            "persistence": "NOT_REQUESTED",
        }


if __name__ == "__main__":
    result = LiveVerificationEngine().execute_live_verification("fortigate")
    print(f"Live verification status: {result['status']}")
