#!/usr/bin/env python3
"""Planning-only remediation governance with sole-owner safety questions."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable

import jsonschema
import yaml

from core.policy.policy_engine import PolicyEngine


class RemediationEngine:
    """Create reviewable change plans; this foundation never invokes a driver."""

    _ACTION_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")
    _OWNER_REFERENCE = "MNE-BRAIN-OWNER"

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.policy_engine = PolicyEngine(base_dir=self.base_dir)
        self.actions_dir = self.base_dir / "actions" / "approved"
        schema_path = self.base_dir / "00_meta" / "schemas" / "action.schema.json"
        self.action_schema = json.loads(schema_path.read_text(encoding="utf-8"))

    def load_action_template(self, action_id: str) -> dict[str, Any]:
        """Load and validate one explicitly named template without path traversal."""
        if not isinstance(action_id, str) or not self._ACTION_ID.fullmatch(action_id):
            raise ValueError("Action ID has an invalid format.")
        action_path = (self.actions_dir / f"{action_id}.yaml").resolve()
        try:
            action_path.relative_to(self.actions_dir.resolve())
        except ValueError as exc:
            raise ValueError("Action template must remain beneath actions/approved/.") from exc
        if not action_path.exists():
            raise FileNotFoundError(f"Action template {action_id!r} was not found.")
        with action_path.open("r", encoding="utf-8") as action_file:
            action_data = yaml.safe_load(action_file) or {}
        if not isinstance(action_data, dict):
            raise ValueError("Action template must contain a mapping.")
        jsonschema.validate(instance=action_data, schema=self.action_schema)
        if action_data.get("action_id") != action_id:
            raise ValueError("Action template ID does not match its file name.")
        return action_data

    @staticmethod
    def _question(passed: bool, status: str, reason: str) -> dict[str, Any]:
        return {"passed": passed, "status": status, "reason": reason}

    @staticmethod
    def _root_cause_is_attributable(root_cause_evidence: Any) -> bool:
        return (
            isinstance(root_cause_evidence, dict)
            and root_cause_evidence.get("reasoning_status") == "EVIDENCE_SUPPORTED"
            and root_cause_evidence.get("stop_early_triggered") is True
            and isinstance(root_cause_evidence.get("conclusive_root_cause"), dict)
            and bool(root_cause_evidence["conclusive_root_cause"].get("id"))
            and isinstance(root_cause_evidence.get("accepted_evidence_refs"), list)
            and bool(root_cause_evidence["accepted_evidence_refs"])
        )

    def evaluate_pre_remediation_questions(
        self,
        action_data: dict[str, Any],
        root_cause_evidence: dict[str, Any] | None = None,
        *,
        owner_reference: str | None = None,
        explicit_owner_instruction: bool = False,
    ) -> dict[str, Any]:
        """Evaluate all safety questions without performing an action."""
        action_id = str(action_data.get("action_id", ""))
        risk_level = action_data.get("risk_level")
        root_cause_passed = self._root_cause_is_attributable(root_cause_evidence)
        template_approved = action_data.get("template_status") == "approved"
        policy_decision = self.policy_engine.evaluate_action_policy(
            risk_level,
            action_id=action_id,
            is_live_verification=risk_level == 0,
        )
        policy_status = policy_decision.get("policy_status")
        prohibited = policy_status == "STRICTLY_PROHIBITED" or policy_decision.get("prohibited") is True
        policy_valid = (
            policy_decision.get("approved") is True
            if risk_level == 0
            else risk_level in (1, 2, 3) and policy_status == "OWNER_INSTRUCTION_REQUIRED"
        ) and not prohibited
        rollback_command = action_data.get("rollback_command")
        rollback_defined = risk_level == 0 or (
            isinstance(rollback_command, str)
            and rollback_command.strip().casefold() not in {"", "none"}
        )
        pre_checks = action_data.get("pre_checks")
        post_checks = action_data.get("post_checks")
        checks_defined = (
            isinstance(pre_checks, list)
            and bool(pre_checks)
            and isinstance(post_checks, list)
            and bool(post_checks)
        )
        owner_instruction_valid = (
            owner_reference == self._OWNER_REFERENCE
            and explicit_owner_instruction is True
        )

        questions = {
            "q1_root_cause_verified": self._question(
                root_cause_passed,
                "PASS" if root_cause_passed else "FAIL",
                "Attributable evidence supports the root cause."
                if root_cause_passed
                else "An evidence-supported reasoning state with evidence references is required.",
            ),
            "q2_template_approved": self._question(
                template_approved,
                "PASS" if template_approved else "FAIL",
                "Template carries explicit sole-owner-reviewed status."
                if template_approved
                else "Directory placement does not grant readiness; template_status must be approved by the sole owner.",
            ),
            "q3_risk_policy": {
                **self._question(
                    policy_valid,
                    "PASS" if policy_valid else "FAIL",
                    "Risk classification is eligible for an explicit owner instruction."
                    if policy_valid
                    else policy_decision.get("reason", "Risk policy rejected the action."),
                ),
                "decision": policy_decision,
            },
            "q4_rollback_defined": self._question(
                rollback_defined,
                "NOT_APPLICABLE" if risk_level == 0 else "PASS" if rollback_defined else "FAIL",
                "Rollback is not required for a read-only plan."
                if risk_level == 0
                else "A non-placeholder rollback command is required for a change.",
            ),
            "q5_pre_post_checks": self._question(
                checks_defined,
                "PASS" if checks_defined else "FAIL",
                "Both pre-checks and post-checks are declared."
                if checks_defined
                else "Both pre-checks and post-checks must be non-empty.",
            ),
            "q6_owner_instruction": self._question(
                owner_instruction_valid,
                "PASS" if owner_instruction_valid else "FAIL",
                "The sole owner explicitly instructed this remediation plan."
                if owner_instruction_valid
                else "Explicit instruction from MNE-BRAIN-OWNER is required.",
            ),
        }
        all_passed = all(question["passed"] for question in questions.values())
        return {
            "all_passed": all_passed,
            "questions": questions,
            "owner_reference": self._OWNER_REFERENCE,
            "audit_mode": "IN_MEMORY_ONLY",
            "retention": "NONE",
            "execution_permitted": False,
        }

    def create_remediation_plan(
        self,
        action_id: str,
        *,
        root_cause_evidence: dict[str, Any] | None = None,
        owner_reference: str | None = None,
        explicit_owner_instruction: bool = False,
    ) -> dict[str, Any]:
        """Return a redacted plan; commands remain inside the local template."""
        try:
            action_data = self.load_action_template(action_id)
        except (FileNotFoundError, ValueError, jsonschema.ValidationError) as exc:
            return {
                "status": "BLOCKED",
                "action_id": action_id,
                "reason": str(exc),
                "execution_permitted": False,
            }

        evaluation = self.evaluate_pre_remediation_questions(
            action_data,
            root_cause_evidence,
            owner_reference=owner_reference,
            explicit_owner_instruction=explicit_owner_instruction,
        )
        canonical_template = json.dumps(action_data, sort_keys=True)
        command = str(action_data.get("command", ""))
        rollback_command = str(action_data.get("rollback_command", ""))
        risk_level = action_data["risk_level"]
        policy_status = evaluation["questions"]["q3_risk_policy"]["decision"].get("policy_status")
        if risk_level == 4 or policy_status == "STRICTLY_PROHIBITED":
            plan_status = "PROHIBITED"
            reason = "Level 4 remediation is prohibited and cannot advance."
        elif evaluation["all_passed"]:
            plan_status = "READY_FOR_SEPARATE_EXECUTION_GATE"
            reason = "All planning checks passed; this component still cannot execute the action."
        else:
            plan_status = "BLOCKED"
            reason = "One or more remediation planning checks failed."
        return {
            "status": plan_status,
            "plan_id": f"rem-{hashlib.sha256(canonical_template.encode('utf-8')).hexdigest()[:12]}",
            "action_id": action_id,
            "title": action_data["title"],
            "template_status": action_data["template_status"],
            "risk_level": risk_level,
            "platform": action_data["platform"],
            "command_fingerprint": hashlib.sha256(command.encode("utf-8")).hexdigest(),
            "rollback_fingerprint": hashlib.sha256(rollback_command.encode("utf-8")).hexdigest(),
            "pre_checks": list(action_data.get("pre_checks", [])),
            "post_checks": list(action_data.get("post_checks", [])),
            "pre_evaluation": evaluation,
            "execution_permitted": False,
            "reason": reason,
        }

    def execute_remediation(
        self,
        action_id: str,
        driver_func: Callable[[str, str], dict[str, Any]] | None = None,
        root_cause_verified: Any = None,
        *,
        owner_reference: str | None = None,
        explicit_owner_instruction: bool = False,
    ) -> dict[str, Any]:
        """Compatibility entry point that intentionally never invokes ``driver_func``."""
        del driver_func
        root_cause_evidence = (
            root_cause_verified if isinstance(root_cause_verified, dict) else None
        )
        plan = self.create_remediation_plan(
            action_id,
            root_cause_evidence=root_cause_evidence,
            owner_reference=owner_reference,
            explicit_owner_instruction=explicit_owner_instruction,
        )
        status = "NOT_EXECUTED" if plan.get("status") == "READY_FOR_SEPARATE_EXECUTION_GATE" else "BLOCKED"
        return {
            "status": status,
            "action_id": action_id,
            "driver_invoked": False,
            "reason": (
                "Remediation is planning-only; an owner-instructed execution bridge is not available."
                if status == "NOT_EXECUTED"
                else plan.get("reason", "Remediation planning was blocked.")
            ),
            "remediation_plan": plan,
        }


if __name__ == "__main__":
    print(RemediationEngine().execute_remediation("level0-read-telemetry")["status"])
