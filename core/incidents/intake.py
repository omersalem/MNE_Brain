#!/usr/bin/env python3
"""Validated, non-persistent P4 incident intake for Ministry operators."""

import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema

from core.incidents.case_manager import IncidentCaseManager
from core.incidents.workflow_governance import IncidentWorkflowGovernance


class IncidentIntakeService:
    """Turn reported incident facts into a bounded P4 case summary."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        schema_path = self.base_dir / "00_meta" / "schemas" / "incident-intake.schema.json"
        self.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.case_manager = IncidentCaseManager(base_dir=self.base_dir)
        self.workflow_governance = IncidentWorkflowGovernance(base_dir=self.base_dir)

    def _validate(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("incident intake must be a JSON object")
        try:
            jsonschema.validate(
                instance=payload,
                schema=self.schema,
                format_checker=jsonschema.FormatChecker(),
            )
        except jsonschema.ValidationError as exc:
            field = ".".join(str(item) for item in exc.absolute_path) or "request"
            raise ValueError(f"incident intake field {field} is invalid: {exc.message}") from exc

        scope = payload["affected_scope"]
        branches = payload.get("branch_references", [])
        user_count = payload.get("affected_user_count")
        if scope == "branch" and len(branches) != 1:
            raise ValueError("branch scope requires exactly one branch reference")
        if scope == "multiple_branches" and len(branches) < 2:
            raise ValueError("multiple_branches scope requires at least two branch references")
        if scope == "single_user" and user_count != 1:
            raise ValueError("single_user scope requires affected_user_count equal to 1")
        if scope == "multiple_users" and (user_count is None or user_count < 2):
            raise ValueError("multiple_users scope requires affected_user_count of at least 2")
        return payload

    @staticmethod
    def _intake_id(payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return f"intake-p4-{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:12]}"

    def create_intake(self, payload: Any) -> dict[str, Any]:
        if self.case_manager.policy.get("safety", {}).get(
            "allow_reported_incident_intake"
        ) is not True:
            raise ValueError("reported incident intake is disabled by P4 policy")
        accepted = self._validate(payload)
        governance = self.workflow_governance.evaluate()
        owner_reference = governance["owner_reference"]
        question = (
            f"{accepted['symptom'].strip()} "
            f"Affected service: {accepted['affected_service'].strip()}. "
            f"Target: {accepted['target_reference'].strip()}"
        )
        impact_context = {
            "affected_service": accepted["affected_service"].strip(),
            "affected_scope": accepted["affected_scope"],
            "availability": accepted["availability"],
            "branch_references": list(accepted.get("branch_references", [])),
            "affected_user_count": accepted.get("affected_user_count"),
            "security_impact_reported": accepted.get("security_impact_reported", False),
            "data_loss_suspected": accepted.get("data_loss_suspected", False),
            "public_service_reported": accepted.get("public_service_reported", False),
            "owner_reference": owner_reference,
            "reporter_reference": accepted.get("incident_reference")
            or owner_reference,
            "reported_at": accepted["reported_at"],
        }
        incident_case = self.case_manager.build_case(question, impact_context=impact_context)
        target = incident_case.get("target")
        priority = incident_case["priority"]
        if target is None:
            intake_status = "NEEDS_TARGET"
        elif priority["classification"] == "UNASSESSED":
            intake_status = "IMPACT_REQUIRED"
        else:
            intake_status = "READY_FOR_EVIDENCE_REVIEW"

        intake_policy = self.case_manager.policy.get("intake", {})
        target_ready = target is not None or not intake_policy.get(
            "require_exact_target_for_evidence_objectives", True
        )
        impact_ready = priority["classification"] != "UNASSESSED" or not intake_policy.get(
            "require_assessed_impact_for_evidence_objectives", True
        )
        evidence_ready = target_ready and impact_ready
        return {
            "intake_id": self._intake_id(accepted),
            "status": intake_status,
            "truth_status": "REPORTED_NOT_VERIFIED",
            "intake": {
                "target_reference": accepted["target_reference"],
                "symptom": accepted["symptom"],
                "affected_service": accepted["affected_service"],
                "affected_scope": accepted["affected_scope"],
                "availability": accepted["availability"],
                "branch_references": list(accepted.get("branch_references", [])),
                "affected_user_count": accepted.get("affected_user_count"),
                "owner_reference": owner_reference,
                "incident_reference": accepted.get("incident_reference"),
                "reported_at": accepted["reported_at"],
            },
            "case": {
                "case_id": incident_case["case_id"],
                "case_state": incident_case["case_state"],
                "target": target,
                "priority": priority,
                "impact": incident_case["impact"],
                "ownership": incident_case["ownership"],
                "runbook_guidance": incident_case["runbook_guidance"],
            },
            "readiness": {
                "target_resolved": target is not None,
                "impact_assessed": priority["classification"] != "UNASSESSED",
                "evidence_request_ready": evidence_ready,
                "owner_priority_confirmation_required": True,
                "owner_controlled": governance["approval_state"] == "OWNER_CONTROLLED",
            },
            "next_evidence_objectives": (
                incident_case.get("pending_checks", []) if evidence_ready else []
            ),
            "workflow_governance": governance,
            "safety": {
                "reported_facts_verified": False,
                "live_connection_attempted": False,
                "external_ai_call_attempted": False,
                "notification_sent": False,
                "persistence_attempted": False,
                "remediation_attempted": False,
            },
        }
