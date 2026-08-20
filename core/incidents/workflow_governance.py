#!/usr/bin/env python3
"""Minimal sole-owner authorization and disabled-capability governance."""

import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml


class IncidentWorkflowGovernance:
    """Expose the sole-owner safety contract without causing side effects."""

    _EXPECTED_POLICY: dict[str, Any] = {
        "approval_state": "OWNER_CONTROLLED",
        "owner_reference": "MNE-BRAIN-OWNER",
        "audit_mode": "IN_MEMORY_ONLY",
        "retention": "NONE",
        "automatic_assignment_enabled": False,
        "ticketing_enabled": False,
        "paging_enabled": False,
        "notifications_enabled": False,
        "automatic_remediation_enabled": False,
        "read_only_authorization": "EXPLICIT_OWNER_PROCEED",
        "configuration_change_authorization": "EXPLICIT_OWNER_INSTRUCTION",
        "remediation_authorization": "EXPLICIT_OWNER_INSTRUCTION",
    }

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        policy_path = self.base_dir / "config" / "p4_incident_policy.yaml"
        policy = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
        self.policy = policy.get("workflow_governance", {})
        schema_path = (
            self.base_dir
            / "00_meta"
            / "schemas"
            / "incident-workflow-governance.schema.json"
        )
        self.schema = json.loads(schema_path.read_text(encoding="utf-8"))

    def evaluate(self) -> dict[str, Any]:
        if self.policy != self._EXPECTED_POLICY:
            raise ValueError("P4 sole-owner governance policy is unsafe or malformed")
        result = {
            "mode": "SOLE_OWNER_GOVERNANCE",
            "approval_state": self.policy["approval_state"],
            "owner_reference": self.policy["owner_reference"],
            "audit_mode": self.policy["audit_mode"],
            "retention": self.policy["retention"],
            "authorization": {
                "read_only_troubleshooting": self.policy["read_only_authorization"],
                "configuration_changes": self.policy[
                    "configuration_change_authorization"
                ],
                "remediation": self.policy["remediation_authorization"],
            },
            "disabled_capabilities": {
                "ticketing_enabled": False,
                "paging_enabled": False,
                "notifications_enabled": False,
                "automatic_assignment_enabled": False,
                "automatic_remediation_enabled": False,
                "persistent_storage_enabled": False,
            },
            "safety": {
                "live_connection_attempted": False,
                "notification_sent": False,
                "persistence_attempted": False,
                "assignment_attempted": False,
                "remediation_attempted": False,
            },
        }
        jsonschema.validate(instance=result, schema=self.schema)
        return result
