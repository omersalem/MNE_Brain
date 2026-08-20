"""Deterministic P8 planning; transport execution and diagnosis stay outside this module."""

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from core.transports.registry import TransportRegistry


class P8TroubleshootingEngine:
    """Build exact, bounded diagnostic plans and compact AI reasoning handoffs."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = Path(base_dir or Path(__file__).resolve().parent.parent.parent)
        schema = json.loads((self.base_dir / "00_meta/schemas/p8-diagnostic-catalog.schema.json").read_text(encoding="utf-8"))
        catalog = yaml.safe_load((self.base_dir / "config/p8_diagnostic_catalog.yaml").read_text(encoding="utf-8")) or {}
        jsonschema.validate(catalog, schema)
        self.policy = yaml.safe_load((self.base_dir / "config/p8_troubleshooting_policy.yaml").read_text(encoding="utf-8")) or {}
        self.catalog = catalog
        self.transport_registry = TransportRegistry(base_dir=self.base_dir)
        self.bindings = {item["binding_id"]: item for item in self.transport_registry.binding_catalog["bindings"]}
        self.reconciliations = {item["binding_id"]: item for item in catalog["reconciliations"]}
        self.scenarios = {item["scenario_id"]: item for item in catalog["scenarios"]}
        self._validate_cross_references()

    def _validate_cross_references(self) -> None:
        if len(self.reconciliations) != len(self.catalog["reconciliations"]):
            raise ValueError("P8 reconciliation binding IDs must be unique.")
        if len(self.scenarios) != len(self.catalog["scenarios"]):
            raise ValueError("P8 scenario IDs must be unique.")
        if set(self.reconciliations) != set(self.bindings):
            raise ValueError("P8 reconciliation must cover every P7 binding exactly once.")
        for scenario in self.scenarios.values():
            unknown = set(scenario["primary_bindings"]).difference(self.bindings)
            if unknown:
                raise ValueError(f"Unknown P8 primary bindings: {sorted(unknown)}")
            for check in scenario["checks"]:
                if check["binding_id"] != "PRIMARY" and check["binding_id"] not in self.bindings:
                    raise ValueError(f"Unknown P8 check binding: {check['binding_id']}")

    def status(self) -> dict[str, Any]:
        dispositions = Counter(item["disposition"] for item in self.reconciliations.values())
        return {
            "phase": "P8",
            "status": "IMPLEMENTED_DISABLED_AT_REST",
            "approval_state": "OWNER_CONTROLLED",
            "owner_reference": "MNE-BRAIN-OWNER",
            "audit_mode": "IN_MEMORY_ONLY",
            "retention": "NONE",
            "scenario_count": len(self.scenarios),
            "scenario_families": sorted(item["family"] for item in self.scenarios.values()),
            "reconciliation_count": len(self.reconciliations),
            "reconciliation_dispositions": dict(sorted(dispositions.items())),
            "catalog": [{"scenario_id": item["scenario_id"], "title": item["title"], "family": item["family"], "primary_bindings": item["primary_bindings"]} for item in self.scenarios.values()],
            "live_enabled": bool(self.policy.get("enabled")),
            "live_connection_attempted": False,
            "raw_output_included": False,
            "persistence_enabled": False,
            "external_ai_enabled": False,
            "remediation_enabled": False,
            "notifications_enabled": False,
            "ticketing_enabled": False,
            "paging_enabled": False,
            "automatic_assignment_enabled": False,
        }

    def _resolve_checks(self, scenario: dict[str, Any], primary_binding: str) -> list[dict[str, Any]]:
        planned: list[dict[str, Any]] = []
        seen: set[str] = set()
        for declared in scenario["checks"]:
            binding_id = primary_binding if declared["binding_id"] == "PRIMARY" else declared["binding_id"]
            if binding_id in seen:
                continue
            binding = self.bindings[binding_id]
            if binding["scope_status"] != "ACTIVE":
                continue
            seen.add(binding_id)
            reconciliation = self.reconciliations[binding_id]
            planned.append({
                "binding_id": binding_id,
                "check_id": binding["check_id"],
                "platform": binding["platform"],
                "protocol": binding["protocol"],
                "objective": declared["objective"],
                "read_only": True,
                "identity_disposition": reconciliation["disposition"],
                "canonical_entity_id": reconciliation["canonical_entity_id"],
                "canonical_promotion_allowed": False,
            })
        return planned[: int(self.policy["maximum_bindings_per_scope"])]

    def _validate_evidence(self, evidence: list[dict[str, Any]], checks: list[dict[str, Any]], now: datetime) -> tuple[list[dict[str, Any]], list[str]]:
        expected = {(item["binding_id"], item["check_id"]) for item in checks}
        accepted: list[dict[str, Any]] = []
        rejected: list[str] = []
        for item in evidence[: int(self.policy["maximum_evidence_records"])]:
            evidence_id = str(item.get("evidence_id", "missing"))[:80]
            try:
                required = ("evidence_id", "binding_id", "check_id", "collected_at", "verification_status", "trust_level", "outcome", "summary")
                if any(key not in item for key in required) or "raw_output" in item:
                    raise ValueError("malformed or raw output supplied")
                if item["verification_status"] != "live_verified" or item["trust_level"] != 5:
                    raise ValueError("not trust-5 live evidence")
                if (item["binding_id"], item["check_id"]) not in expected:
                    raise ValueError("outside planned scope")
                collected = datetime.fromisoformat(str(item["collected_at"]).replace("Z", "+00:00"))
                age = (now - collected.astimezone(timezone.utc)).total_seconds()
                if age < -30 or age > int(self.policy["evidence_freshness_seconds"]):
                    raise ValueError("stale or future evidence")
                summary = str(item["summary"])
                if not summary or len(summary) > 240:
                    raise ValueError("summary outside bounds")
                accepted.append({key: item[key] for key in required})
            except (TypeError, ValueError) as exc:
                rejected.append(f"{evidence_id}: {exc}")
        return accepted, rejected

    def plan(self, request: dict[str, Any]) -> dict[str, Any]:
        scenario_id = str(request.get("scenario_id", "")).strip()
        binding_id = str(request.get("binding_id", "")).strip()
        symptom = str(request.get("symptom", "")).strip()[:500]
        if scenario_id not in self.scenarios:
            raise ValueError("One exact registered P8 scenario_id is required.")
        scenario = self.scenarios[scenario_id]
        if binding_id in self.bindings and self.bindings[binding_id]["scope_status"] != "ACTIVE":
            raise ValueError("The selected binding is owner-excluded.")
        if binding_id not in scenario["primary_bindings"]:
            raise ValueError("The exact primary binding is not permitted for this scenario.")
        binding = self.bindings[binding_id]
        checks = self._resolve_checks(scenario, binding_id)
        now = datetime.now(timezone.utc)
        accepted, rejected = self._validate_evidence(list(request.get("evidence") or []), checks, now)
        keywords = [keyword for keyword in scenario["symptom_keywords"] if keyword.casefold() in symptom.casefold()]
        evidence_status = "LIVE_EVIDENCE_ACCEPTED" if accepted else "EVIDENCE_REQUIRED"
        unknowns = [item["objective"] for item in checks if not any(ev["binding_id"] == item["binding_id"] and ev["check_id"] == item["check_id"] for ev in accepted)]
        handoff = {
            "scenario": {"id": scenario_id, "family": scenario["family"], "symptom": symptom or "NOT_PROVIDED"},
            "primary": {"binding_id": binding_id, "canonical_entity_id": self.reconciliations[binding_id]["canonical_entity_id"], "identity_disposition": self.reconciliations[binding_id]["disposition"]},
            "accepted_evidence": accepted,
            "unknowns": unknowns,
            "reasoning_instruction": "Use only accepted evidence. Compare independent components, state confidence and unknowns, and recommend only the next read-only check. Do not infer root cause from reachability alone.",
        }
        handoff_json = json.dumps(handoff, separators=(",", ":"), ensure_ascii=True)
        if len(handoff_json) > int(self.policy["handoff_character_budget"]):
            raise ValueError("P8 handoff exceeds its character budget.")
        return {
            "status": evidence_status,
            "scenario": {"scenario_id": scenario_id, "title": scenario["title"], "family": scenario["family"], "matched_symptom_keywords": keywords},
            "primary": {"binding_id": binding_id, "canonical_entity_id": self.reconciliations[binding_id]["canonical_entity_id"], "identity_disposition": self.reconciliations[binding_id]["disposition"]},
            "planned_checks": checks,
            "accepted_evidence": accepted,
            "rejected_evidence": rejected,
            "confidence": "UNASSESSED_BY_DETERMINISTIC_PLANNER",
            "root_cause": None,
            "unknowns": unknowns,
            "next_check": checks[0] if checks else None,
            "action": "OWNER_MAY_PROCEED_WITH_EXACT_READ_ONLY_SCOPE" if not accepted else "HAND_OFF_TO_EVIDENCE_BOUNDED_REASONING",
            "ai_handoff": handoff,
            "metrics": {"bindings": len(checks), "evidence_records": len(accepted), "handoff_chars": len(handoff_json), "evidence_token_estimate": (len(handoff_json) + 3) // 4},
            "safety": {"live_connection_attempted": False, "raw_output_included": False, "persistence_attempted": False, "external_ai_call_attempted": False, "remediation_attempted": False, "notifications_sent": False, "ticket_created": False, "page_sent": False, "automatic_assignment_attempted": False},
        }
