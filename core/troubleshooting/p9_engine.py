"""P9 adaptive deep-diagnostic planning and evidence-bounded AI handoff."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from core.transports.registry import TransportRegistry


class P9DiagnosticEngine:
    WRITE_TOKENS = re.compile(r"\b(?:set|add|remove|restart|stop|start|new|clear|delete|write|save|execute|reboot|shutdown|format|copy|move|rename|enable|disable|install|update|modify|create)\b", re.IGNORECASE)
    SENSITIVE_KEYS = re.compile(r"(?:raw|password|secret|credential|username|token|command|operation)", re.IGNORECASE)

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = Path(base_dir or Path(__file__).resolve().parent.parent.parent)
        schema = json.loads((self.base_dir / "00_meta/schemas/p9-diagnostic-catalog.schema.json").read_text(encoding="utf-8"))
        catalog = yaml.safe_load((self.base_dir / "config/p9_diagnostic_catalog.yaml").read_text(encoding="utf-8")) or {}
        jsonschema.validate(catalog, schema)
        self.policy = yaml.safe_load((self.base_dir / "config/p9_troubleshooting_policy.yaml").read_text(encoding="utf-8")) or {}
        self.catalog = catalog
        self.scenarios = {item["scenario_id"]: item for item in catalog["scenarios"]}
        registry = TransportRegistry(base_dir=self.base_dir)
        self.bindings = {item["binding_id"]: item for item in registry.binding_catalog["bindings"]}
        self._validate_catalog()

    def _validate_catalog(self) -> None:
        if len(self.scenarios) != len(self.catalog["scenarios"]):
            raise ValueError("P9 scenario IDs must be unique.")
        check_ids: set[str] = set()
        for scenario in self.scenarios.values():
            if unknown := set(scenario["primary_bindings"]).difference(self.bindings):
                raise ValueError(f"Unknown P9 primary bindings: {sorted(unknown)}")
            resolved_bindings: set[str] = set()
            for check in scenario["checks"]:
                if check["check_id"] in check_ids:
                    raise ValueError("P9 check IDs must be globally unique.")
                check_ids.add(check["check_id"])
                binding_id = check["binding_id"]
                if binding_id != "PRIMARY" and binding_id not in self.bindings:
                    raise ValueError(f"Unknown P9 check binding: {binding_id}")
                policy_operation = check["operation"].replace("-ErrorAction Stop", "")
                if any(character in check["operation"] for character in ("\r", "\n", "\x00")) or self.WRITE_TOKENS.search(policy_operation):
                    raise ValueError(f"Mutating or malformed P9 operation: {check['check_id']}")
                if binding_id != "PRIMARY":
                    resolved_bindings.add(binding_id)
            if len(resolved_bindings) + 1 > int(self.policy["maximum_bindings_per_scope"]):
                raise ValueError(f"P9 scenario exceeds binding budget: {scenario['scenario_id']}")

    def status(self) -> dict[str, Any]:
        return {
            "phase": "P9", "status": "IMPLEMENTED_DISABLED_AT_REST",
            "approval_state": "OWNER_CONTROLLED", "owner_reference": "MNE-BRAIN-OWNER",
            "audit_mode": "IN_MEMORY_ONLY", "retention": "NONE",
            "scenario_count": len(self.scenarios),
            "check_count": sum(len(item["checks"]) for item in self.scenarios.values()),
            "catalog": [{"scenario_id": item["scenario_id"], "title": item["title"], "family": item["family"], "primary_bindings": item["primary_bindings"], "known_gap": item["known_gap"]} for item in self.scenarios.values()],
            "live_enabled": bool(self.policy["enabled"]), "live_connection_attempted": False,
            "raw_output_included": False, "operations_included": False,
            "persistence_enabled": False, "external_ai_enabled": False,
            "automatic_diagnosis_enabled": False, "remediation_enabled": False,
            "notifications_enabled": False, "ticketing_enabled": False,
            "paging_enabled": False, "automatic_assignment_enabled": False,
        }

    def resolved_checks(self, scenario_id: str, primary_binding: str) -> list[dict[str, Any]]:
        if scenario_id not in self.scenarios:
            raise ValueError("One exact registered P9 scenario_id is required.")
        scenario = self.scenarios[scenario_id]
        if primary_binding in self.bindings and self.bindings[primary_binding]["scope_status"] != "ACTIVE":
            raise ValueError("The selected binding is owner-excluded.")
        if primary_binding not in scenario["primary_bindings"]:
            raise ValueError("The exact primary binding is not permitted for this P9 scenario.")
        resolved = []
        for item in scenario["checks"]:
            check = dict(item)
            check["binding_id"] = primary_binding if item["binding_id"] == "PRIMARY" else item["binding_id"]
            if self.bindings[check["binding_id"]]["scope_status"] == "ACTIVE":
                resolved.append(check)
        if len({item["binding_id"] for item in resolved}) > int(self.policy["maximum_bindings_per_scope"]):
            raise ValueError("Resolved P9 scope exceeds the binding budget.")
        return sorted(resolved, key=lambda item: (item["stage"], -item["information_gain"], item["check_id"]))

    @staticmethod
    def _public_check(check: dict[str, Any]) -> dict[str, Any]:
        return {key: check[key] for key in ("check_id", "binding_id", "normalizer", "stage", "information_gain", "objective", "read_only")}

    def _validate_evidence(self, supplied: list[dict[str, Any]], checks: list[dict[str, Any]], now: datetime) -> tuple[list[dict[str, Any]], list[str]]:
        expected = {(item["binding_id"], item["check_id"]) for item in checks}
        accepted, rejected = [], []
        required = ("evidence_id", "binding_id", "check_id", "collected_at", "verification_status", "trust_level", "outcome", "summary", "observations", "output_sha256_prefix")
        for item in supplied[: int(self.policy["maximum_evidence_records"])]:
            evidence_id = str(item.get("evidence_id", "missing"))[:80]
            try:
                if any(key not in item for key in required) or any(self.SENSITIVE_KEYS.search(str(key)) for key in item if key not in required):
                    raise ValueError("malformed or sensitive field supplied")
                if item["verification_status"] != "live_verified" or item["trust_level"] != 5 or item["outcome"] not in ("SUCCESS", "FAILED"):
                    raise ValueError("not attributable trust-5 live evidence")
                if (item["binding_id"], item["check_id"]) not in expected:
                    raise ValueError("outside planned scope")
                collected = datetime.fromisoformat(str(item["collected_at"]).replace("Z", "+00:00"))
                age = (now - collected.astimezone(timezone.utc)).total_seconds()
                if age < -30 or age > int(self.policy["evidence_freshness_seconds"]):
                    raise ValueError("stale or future evidence")
                observations = item["observations"]
                if not isinstance(observations, dict) or any(self.SENSITIVE_KEYS.search(str(key)) for key in observations):
                    raise ValueError("unsafe observations")
                if len(json.dumps(observations, ensure_ascii=True)) > 2000 or len(str(item["summary"])) > 240:
                    raise ValueError("evidence exceeds compact bounds")
                accepted.append({key: item[key] for key in required})
            except (TypeError, ValueError) as exc:
                rejected.append(f"{evidence_id}: {exc}")
        return accepted, rejected

    def _assessment(self, supplied: Any, accepted: list[dict[str, Any]]) -> dict[str, Any] | None:
        if supplied is None:
            return None
        if not isinstance(supplied, dict):
            raise ValueError("Reasoning assessment must be an object.")
        refs = supplied.get("evidence_refs")
        valid_refs = {item["evidence_id"] for item in accepted}
        confidence = supplied.get("confidence")
        if not isinstance(refs, list) or not refs or not set(refs).issubset(valid_refs):
            raise ValueError("Reasoning assessment references unaccepted evidence.")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ValueError("Reasoning confidence must be between zero and one.")
        root_cause = supplied.get("root_cause")
        if root_cause is not None and (not isinstance(root_cause, str) or not root_cause.strip() or len(root_cause) > 400):
            raise ValueError("Reasoning root cause is outside bounds.")
        return {"root_cause": root_cause, "confidence": float(confidence), "evidence_refs": list(refs), "unknowns": [str(item)[:160] for item in supplied.get("unknowns", [])[:8]], "action": str(supplied.get("action", "OWNER_REVIEW_REQUIRED"))[:200]}

    def plan(self, request: dict[str, Any]) -> dict[str, Any]:
        scenario_id = str(request.get("scenario_id", "")).strip()
        binding_id = str(request.get("binding_id", "")).strip()
        symptom = str(request.get("symptom", "")).strip()[:500]
        checks = self.resolved_checks(scenario_id, binding_id)
        scenario = self.scenarios[scenario_id]
        now = datetime.now(timezone.utc)
        accepted, rejected = self._validate_evidence(list(request.get("evidence") or []), checks, now)
        assessment = self._assessment(request.get("reasoning_assessment"), accepted)
        completed = {(item["binding_id"], item["check_id"]) for item in accepted}
        candidates = [item for item in checks if (item["binding_id"], item["check_id"]) not in completed]
        next_check = self._public_check(candidates[0]) if candidates else None
        stop_early = bool(assessment and assessment["root_cause"] and assessment["confidence"] >= float(self.policy["stop_early_confidence"]))
        if stop_early:
            status = "STOP_EARLY_EVIDENCE_BOUND"
        elif assessment and assessment["root_cause"]:
            status = "PROBABLE_CAUSE_OWNER_REVIEW"
        elif accepted:
            status = "READY_FOR_AI_REASONING" if not candidates else "MORE_EVIDENCE_AVAILABLE"
        else:
            status = "EVIDENCE_REQUIRED"
        unknowns = [item["objective"] for item in candidates]
        if scenario["known_gap"]:
            unknowns.append(scenario["known_gap"])
        handoff = {
            "scenario": {"id": scenario_id, "family": scenario["family"], "symptom": symptom or "NOT_PROVIDED"},
            "primary_binding": binding_id,
            "accepted_evidence": accepted,
            "remaining_objectives": unknowns,
            "instruction": "Reason only from accepted evidence. Correlate independent layers, cite evidence IDs, state confidence and unknowns, and propose at most one next read-only check. Do not infer causality from management reachability alone.",
        }
        serialized = json.dumps(handoff, separators=(",", ":"), ensure_ascii=True)
        if len(serialized) > int(self.policy["handoff_character_budget"]):
            raise ValueError("P9 handoff exceeds its character budget.")
        return {
            "status": status,
            "scenario": {"scenario_id": scenario_id, "title": scenario["title"], "family": scenario["family"]},
            "primary_binding": binding_id,
            "known_gap": scenario["known_gap"],
            "accepted_evidence": accepted,
            "rejected_evidence": rejected,
            "candidate_checks": [self._public_check(item) for item in candidates],
            "next_check": next_check,
            "root_cause": assessment["root_cause"] if assessment else None,
            "confidence": assessment["confidence"] if assessment else 0.0,
            "unknowns": assessment["unknowns"] if assessment else unknowns,
            "action": assessment["action"] if assessment else ("HAND_OFF_TO_AI_REASONING" if accepted and not candidates else "RUN_EXACT_NEXT_READ_ONLY_CHECK"),
            "stop_early": stop_early,
            "ai_handoff": handoff,
            "metrics": {"bindings": len({item["binding_id"] for item in checks}), "accepted_evidence": len(accepted), "remaining_checks": len(candidates), "handoff_chars": len(serialized), "handoff_token_estimate": (len(serialized) + 3) // 4},
            "safety": {"live_connection_attempted": False, "raw_output_included": False, "operations_included": False, "persistence_attempted": False, "external_ai_call_attempted": False, "automatic_diagnosis_attempted": False, "remediation_attempted": False, "notifications_sent": False, "ticket_created": False, "page_sent": False, "automatic_assignment_attempted": False, "canonical_promotion_attempted": False},
        }
