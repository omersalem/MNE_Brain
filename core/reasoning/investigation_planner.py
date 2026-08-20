#!/usr/bin/env python3
"""Evidence-gated investigation planning without device-side execution."""

import math
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


class InvestigationPlanner:
    """Prioritize diagnostic hypotheses while preserving evidence boundaries.

    This planner never collects telemetry or authorizes an action. It can only
    return an evidence-scoped conclusion when it receives attributable, fresh
    live evidence from the evidence-pack layer.
    """

    DEFAULT_HYPOTHESES = (
        {
            "id": "h1_interface_down",
            "description": "Physical interface or link is down",
            "probability": 0.4,
        },
        {
            "id": "h2_routing_issue",
            "description": "Routing or reachability path is impaired",
            "probability": 0.3,
        },
        {
            "id": "h3_firewall_policy",
            "description": "A security policy is denying the required flow",
            "probability": 0.3,
        },
    )

    _SIGNALS = (
        (
            "h1_interface_down",
            re.compile(r"\b(?:interface|link|port)\s+(?:is\s+)?down\b|\bstatus\s+down\b"),
        ),
        (
            "h3_firewall_policy",
            re.compile(r"\b(?:deny|denied|blocked|drop|dropped)\b"),
        ),
    )

    def __init__(self, certainty_threshold: float = 0.95):
        if not 0 < certainty_threshold <= 1:
            raise ValueError("certainty_threshold must be greater than 0 and at most 1")
        self.certainty_threshold = certainty_threshold

    @staticmethod
    def _normalise_hypotheses(hypotheses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Copy and validate candidate hypotheses without mutating caller data."""
        candidate_hypotheses = deepcopy(hypotheses or list(InvestigationPlanner.DEFAULT_HYPOTHESES))
        seen_ids: set[str] = set()
        total_probability = 0.0

        for hypothesis in candidate_hypotheses:
            hypothesis_id = hypothesis.get("id")
            description = hypothesis.get("description")
            try:
                probability = float(hypothesis.get("probability"))
            except (TypeError, ValueError) as exc:
                raise ValueError("Each hypothesis probability must be numeric") from exc
            if not isinstance(hypothesis_id, str) or not hypothesis_id or hypothesis_id in seen_ids:
                raise ValueError("Each hypothesis must have a unique, non-empty id")
            if not isinstance(description, str) or not description:
                raise ValueError("Each hypothesis must have a non-empty description")
            if probability < 0:
                raise ValueError("Hypothesis probabilities cannot be negative")
            seen_ids.add(hypothesis_id)
            total_probability += probability
            hypothesis["probability"] = probability

        if not candidate_hypotheses or total_probability <= 0:
            raise ValueError("At least one hypothesis must have a positive probability")
        for hypothesis in candidate_hypotheses:
            hypothesis["probability"] = round(hypothesis["probability"] / total_probability, 4)
        return candidate_hypotheses

    @staticmethod
    def calculate_entropy(probabilities: list[float]) -> float:
        """Calculate Shannon entropy for a valid probability distribution."""
        if not probabilities:
            return 0.0
        if any(probability < 0 for probability in probabilities):
            raise ValueError("Entropy probabilities cannot be negative")
        total_probability = sum(probabilities)
        if not math.isclose(total_probability, 1.0, abs_tol=0.001):
            raise ValueError("Entropy probabilities must sum to 1")
        return round(
            -sum(probability * math.log2(probability) for probability in probabilities if probability > 0),
            4,
        )

    def calculate_information_gain(self, initial_probs: list[float], new_probs: list[float]) -> float:
        """Calculate information gain only across the same hypothesis space."""
        if len(initial_probs) != len(new_probs):
            raise ValueError("Information-gain distributions must have the same length")
        return round(
            self.calculate_entropy(initial_probs) - self.calculate_entropy(new_probs),
            4,
        )

    @staticmethod
    def _is_attributable_live_evidence(evidence: dict[str, Any]) -> tuple[bool, str]:
        """Reject raw assertions and incomplete records before reasoning on them."""
        required_fields = (
            "entity_id",
            "source_file",
            "source",
            "observed_at",
            "evidence_refs",
            "verification_target",
            "verification_check_id",
            "verification_outcome",
            "content",
        )
        missing = [field for field in required_fields if not evidence.get(field)]
        if evidence.get("evidence_status") != "live_verified":
            return False, "evidence_status is not live_verified"
        if evidence.get("trust_level") != 5:
            return False, "trust_level is not 5"
        if missing:
            return False, f"missing attribution fields: {', '.join(missing)}"
        if evidence.get("verification_outcome") != "success":
            return False, "verification_outcome is not success"
        if not isinstance(evidence["evidence_refs"], list) or not all(evidence["evidence_refs"]):
            return False, "evidence_refs must be a non-empty list"
        try:
            observed_at = datetime.fromisoformat(str(evidence["observed_at"]).replace("Z", "+00:00"))
        except ValueError:
            return False, "observed_at is not an ISO-8601 timestamp"
        if observed_at.tzinfo is None or observed_at.astimezone(timezone.utc) > datetime.now(timezone.utc):
            return False, "observed_at must be timezone-aware and not in the future"
        return True, "accepted"

    @classmethod
    def _detect_signal(cls, content: str) -> str | None:
        lowered_content = content.casefold()
        for hypothesis_id, pattern in cls._SIGNALS:
            if pattern.search(lowered_content):
                return hypothesis_id
        return None

    def _focus_hypothesis(
        self, hypotheses: list[dict[str, Any]], supported_hypothesis_id: str
    ) -> list[dict[str, Any]]:
        """Focus probability only where accepted evidence names a known hypothesis."""
        if not any(hypothesis["id"] == supported_hypothesis_id for hypothesis in hypotheses):
            return hypotheses

        remainder = len(hypotheses) - 1
        residual_probability = (1 - self.certainty_threshold) / remainder if remainder else 0.0
        focused: list[dict[str, Any]] = []
        for hypothesis in hypotheses:
            updated = dict(hypothesis)
            updated["probability"] = self.certainty_threshold if hypothesis["id"] == supported_hypothesis_id else residual_probability
            focused.append(updated)
        return focused

    def evaluate_investigation_state(
        self,
        hypotheses: list[dict[str, Any]] | None,
        telemetry_evidence: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Assess evidence without issuing a live-verification or remediation command."""
        initial_hypotheses = self._normalise_hypotheses(hypotheses or [])
        accepted_evidence_refs: list[str] = []
        evidence_assessment: list[dict[str, str]] = []
        supported_hypotheses: set[str] = set()

        for evidence in telemetry_evidence or []:
            valid, reason = self._is_attributable_live_evidence(evidence)
            reference = str((evidence.get("evidence_refs") or ["unattributed"])[0])
            if not valid:
                evidence_assessment.append({"evidence_ref": reference, "status": "ignored", "reason": reason})
                continue

            accepted_evidence_refs.extend(str(item) for item in evidence["evidence_refs"])
            check_id = str(evidence.get("verification_check_id", ""))
            signal_hypothesis_id = (
                None
                if check_id == "interface_stats"
                else self._detect_signal(str(evidence["content"]))
            )
            if signal_hypothesis_id is None:
                reason = (
                    "Interface inventory requires affected-port correlation before diagnosis."
                    if check_id == "interface_stats"
                    else "No supported diagnostic signal."
                )
                evidence_assessment.append(
                    {"evidence_ref": reference, "status": "accepted_but_inconclusive", "reason": reason}
                )
            elif any(hypothesis["id"] == signal_hypothesis_id for hypothesis in initial_hypotheses):
                supported_hypotheses.add(signal_hypothesis_id)
                evidence_assessment.append(
                    {"evidence_ref": reference, "status": "accepted", "reason": f"Supports {signal_hypothesis_id}."}
                )
            else:
                evidence_assessment.append(
                    {"evidence_ref": reference, "status": "accepted_but_out_of_scope", "reason": "Signal does not map to a supplied hypothesis."}
                )

        updated_hypotheses = initial_hypotheses
        conclusive_root_cause: dict[str, Any] | None = None
        stop_early = False
        if len(supported_hypotheses) == 1:
            supported_hypothesis_id = next(iter(supported_hypotheses))
            updated_hypotheses = self._focus_hypothesis(initial_hypotheses, supported_hypothesis_id)
            conclusive_root_cause = next(
                hypothesis for hypothesis in updated_hypotheses if hypothesis["id"] == supported_hypothesis_id
            )
            stop_early = conclusive_root_cause["probability"] >= self.certainty_threshold
            reasoning_status = "EVIDENCE_SUPPORTED"
            next_action = "RETURN_EVIDENCE_SCOPED_CONCLUSION"
        elif len(supported_hypotheses) > 1:
            reasoning_status = "CONFLICTING_EVIDENCE"
            next_action = "REQUEST_POLICY_EVALUATION"
        else:
            reasoning_status = "PENDING_EVIDENCE"
            next_action = "REQUEST_POLICY_EVALUATION"

        information_gain = self.calculate_information_gain(
            [hypothesis["probability"] for hypothesis in initial_hypotheses],
            [hypothesis["probability"] for hypothesis in updated_hypotheses],
        )
        return {
            "hypotheses": updated_hypotheses,
            "information_gain": information_gain,
            "reasoning_status": reasoning_status,
            "stop_early_triggered": stop_early,
            "conclusive_root_cause": conclusive_root_cause,
            "accepted_evidence_refs": sorted(set(accepted_evidence_refs)),
            "evidence_assessment": evidence_assessment,
            "next_action": next_action,
        }
