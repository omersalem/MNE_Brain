#!/usr/bin/env python3
"""Deterministic policy decisions; this module never performs an operation."""

from pathlib import Path
from typing import Any

import yaml


class PolicyEngine:
    """Apply explicit live-verification and remediation safety gates."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.config_path = self.base_dir / "config" / "action_policy.yaml"
        self.policy_data = self._load_policy()

    def _load_policy(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        with self.config_path.open("r", encoding="utf-8") as policy_file:
            return yaml.safe_load(policy_file) or {}

    def _live_verification_gate(self, *, required: bool, authorization_granted: bool) -> dict[str, Any]:
        live_policy = self.policy_data.get("live_verification", {})
        policy_enabled = bool(live_policy.get("enabled", False))
        requires_explicit_authorization = bool(
            live_policy.get("requires_explicit_authorization", True)
        )
        policy_reason = live_policy.get(
            "reason", "No live-verification policy reason is configured."
        )

        if not required:
            return {
                "live_verification_allowed": False,
                "execution_status": "NOT_REQUIRED",
                "policy_reason": policy_reason,
            }
        if not policy_enabled:
            return {
                "live_verification_allowed": False,
                "execution_status": "DISABLED_BY_POLICY",
                "policy_reason": policy_reason,
            }
        if requires_explicit_authorization and not authorization_granted:
            return {
                "live_verification_allowed": False,
                "execution_status": "PENDING_AUTHORIZATION",
                "policy_reason": "Explicit live-verification authorization has not been supplied.",
            }
        return {
            "live_verification_allowed": True,
            "execution_status": "AUTHORIZED",
            "policy_reason": policy_reason,
        }

    def evaluate_verification_necessity(
        self,
        route_type: str,
        has_current_live_evidence: bool = False,
        *,
        authorization_granted: bool = False,
    ) -> dict[str, Any]:
        """Decide whether current-state evidence is needed, then apply its safety gate.

        ``has_current_live_evidence`` must only be true for accepted, fresh,
        attributable live evidence. Documented or unverified knowledge does not
        satisfy this parameter.
        """
        if route_type == "troubleshoot":
            required = True
            reason = "Troubleshooting requires target-specific read-only evidence before a current-state conclusion."
        elif route_type == "asset" and not has_current_live_evidence:
            required = True
            reason = "The asset lacks accepted current live evidence."
        elif route_type == "asset":
            required = False
            reason = "Accepted current live evidence is already available for the asset."
        elif route_type == "concept":
            required = False
            reason = "A concept question can receive a documented-context response."
        else:
            required = True
            reason = "The route type is unknown; current-state claims require policy-governed evidence."

        gate = self._live_verification_gate(
            required=required, authorization_granted=authorization_granted
        )
        return {
            "live_verification_required": required,
            "live_verification_allowed": gate["live_verification_allowed"],
            "execution_status": gate["execution_status"],
            "reason": reason,
            "policy_reason": gate["policy_reason"],
        }

    def evaluate_action_policy(
        self,
        risk_level: int,
        action_id: str = "",
        *,
        is_live_verification: bool = False,
        authorization_granted: bool = False,
    ) -> dict[str, Any]:
        """Classify an action policy; a positive result is never driver execution."""
        if isinstance(risk_level, bool) or not isinstance(risk_level, int) or risk_level not in range(5):
            return {
                "approved": False,
                "risk_level": risk_level,
                "policy_status": "INVALID_RISK_LEVEL",
                "reason": f"Unknown risk level {risk_level!r}.",
            }

        level_key = f"level_{risk_level}"
        level_info = self.policy_data.get("risk_levels", {}).get(level_key, {})
        policy_name = level_info.get("name", f"Level {risk_level}")
        if risk_level == 0 and is_live_verification:
            verification_gate = self._live_verification_gate(
                required=True, authorization_granted=authorization_granted
            )
            return {
                "approved": verification_gate["live_verification_allowed"],
                "risk_level": 0,
                "action_id": action_id,
                "policy_name": policy_name,
                "policy_status": verification_gate["execution_status"],
                "requires_owner_proceed": bool(
                    self.policy_data.get("live_verification", {}).get(
                        "requires_explicit_authorization", True
                    )
                ),
                "reason": verification_gate["policy_reason"],
            }
        if risk_level == 0:
            return {
                "approved": True,
                "risk_level": 0,
                "action_id": action_id,
                "policy_name": policy_name,
                "policy_status": "READ_ONLY_CLASSIFIED",
                "requires_owner_instruction": False,
                "reason": "Level 0 policy classification is read-only; driver execution remains a separate gate.",
            }
        if risk_level == 4:
            return {
                "approved": False,
                "risk_level": 4,
                "action_id": action_id,
                "policy_name": policy_name,
                "policy_status": "STRICTLY_PROHIBITED",
                "prohibited": True,
                "reason": "Level 4 emergency core changes are hard-blocked by policy.",
            }
        return {
            "approved": False,
            "risk_level": risk_level,
            "action_id": action_id,
            "policy_name": policy_name,
            "policy_status": "OWNER_INSTRUCTION_REQUIRED",
            "requires_owner_instruction": True,
            "reason": f"Level {risk_level} change requires an explicit MNE-BRAIN-OWNER instruction and a separate execution gate.",
        }
