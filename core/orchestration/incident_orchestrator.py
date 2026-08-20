#!/usr/bin/env python3
"""Evidence-bounded offline incident orchestration for MNE_Brain P3."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from core.entity.build_entity_index import EntityIndexBuilder
from core.evidence.build_evidence_pack import EvidencePackBuilder
from core.policy.policy_engine import PolicyEngine
from core.reasoning.investigation_planner import InvestigationPlanner
from core.router.route_query import QueryRouter


class IncidentOrchestrator:
    """Assemble a bounded investigation without collecting or changing anything.

    Deterministic code resolves scope, validates evidence, selects evidence
    objectives, and builds a compact context. Diagnosis remains the AI's job and
    is allowed only when the existing reasoning gate accepts attributable live
    evidence.
    """

    MODE = "OFFLINE_NON_EXECUTING"

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.policy_path = self.base_dir / "config" / "p3_troubleshooting_policy.yaml"
        self.schema_path = self.base_dir / "00_meta" / "schemas" / "investigation.schema.json"
        self.policy = self._load_mapping(self.policy_path)
        self.schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        self.limits = self.policy.get("limits", {})
        self.router = QueryRouter(base_dir=self.base_dir)
        self.entity_builder = EntityIndexBuilder(base_dir=self.base_dir)
        self.evidence_builder = EvidencePackBuilder(base_dir=self.base_dir)
        self.reasoning = InvestigationPlanner()
        self.policy_engine = PolicyEngine(base_dir=self.base_dir)

    @staticmethod
    def _load_mapping(path: Path) -> dict[str, Any]:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"{path.name} must contain a mapping")
        return payload

    @staticmethod
    def _investigation_id(question: str, entity_id: str = "unresolved") -> str:
        digest = hashlib.sha256(f"{entity_id}\x00{question}".encode("utf-8")).hexdigest()[:12]
        return f"inv-p3-{digest}"

    @staticmethod
    def _target_view(entity: dict[str, Any]) -> dict[str, Any]:
        return {
            "entity_id": entity["entity_id"],
            "name": entity["name"],
            "category": entity["category"],
            "services": list(entity.get("services", [])),
            "owner": entity.get("owner", ""),
            "knowledge_status": entity.get("knowledge_status", "unverified"),
            "canonical_file": entity.get("canonical_file", ""),
            "operational_state": "UNKNOWN",
        }

    def _dependency_context(
        self, target: dict[str, Any], all_entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Return bounded declared adjacency without claiming dependency or health."""
        by_id = {entity["entity_id"]: entity for entity in all_entities}
        relationships: dict[str, dict[str, Any]] = {}

        for entity_id in target.get("related_entities", []):
            related = by_id.get(entity_id)
            if related:
                relationships[entity_id] = {
                    "entity_id": entity_id,
                    "name": related["name"],
                    "category": related["category"],
                    "relationship": "declared_relation",
                    "knowledge_status": related.get("knowledge_status", "unverified"),
                    "operational_state": "UNKNOWN",
                }

        for entity in all_entities:
            if target["entity_id"] in entity.get("related_entities", []):
                relationships.setdefault(
                    entity["entity_id"],
                    {
                        "entity_id": entity["entity_id"],
                        "name": entity["name"],
                        "category": entity["category"],
                        "relationship": "reverse_declared_relation",
                        "knowledge_status": entity.get("knowledge_status", "unverified"),
                        "operational_state": "UNKNOWN",
                    },
                )

        limit = int(self.limits.get("max_related_entities", 6))
        return [relationships[key] for key in sorted(relationships)[:limit]]

    def _next_checks(
        self,
        target: dict[str, Any],
        dependencies: list[dict[str, Any]],
        reasoning_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if reasoning_state.get("reasoning_status") == "EVIDENCE_SUPPORTED":
            return []

        category = target.get("category")
        services = set(target.get("services", []))
        selected: list[dict[str, Any]] = []
        for check in self.policy.get("check_catalog", []):
            if not isinstance(check, dict):
                continue
            categories = set(check.get("categories", []))
            check_services = set(check.get("services", []))
            if category not in categories and not services.intersection(check_services):
                continue
            selected.append(
                {
                    "check_id": str(check.get("check_id", "")),
                    "priority": int(check.get("priority", 100)),
                    "target_entity_id": target["entity_id"],
                    "objective": str(check.get("objective", "")),
                    "required_evidence": str(check.get("required_evidence", "")),
                    "related_entity_ids": [item["entity_id"] for item in dependencies[:3]],
                    "execution_state": "NOT_RUN",
                    "requires_p2_live_approval": True,
                }
            )

        limit = int(self.limits.get("max_next_checks", 5))
        return sorted(selected, key=lambda item: (item["priority"], item["check_id"]))[:limit]

    def _ai_handoff(
        self,
        question: str,
        target: dict[str, Any] | None,
        dependencies: list[dict[str, Any]],
        evidence_pack: dict[str, Any],
        reasoning_state: dict[str, Any],
        next_checks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        evidence = [
            {
                "entity_id": block.get("entity_id"),
                "evidence_status": block.get("evidence_status"),
                "trust_level": block.get("trust_level"),
                "observed_at": block.get("observed_at"),
                "evidence_refs": block.get("evidence_refs", []),
                "check_id": block.get("verification_check_id", ""),
                "content": str(block.get("content", ""))[:700],
            }
            for block in evidence_pack.get("evidence_blocks", [])
        ]
        handoff = {
            "instruction": (
                "Reason only from accepted evidence. Treat documented relationships as context, "
                "not health or causality. State unknowns. Do not claim root cause or recommend a "
                "change unless attributable live evidence supports it and policy separately permits it."
            ),
            "question": question,
            "target": target,
            "documented_adjacency": dependencies,
            "accepted_evidence": evidence,
            "unknowns": list(evidence_pack.get("unknowns", [])),
            "reasoning_status": reasoning_state.get("reasoning_status"),
            "accepted_evidence_refs": list(reasoning_state.get("accepted_evidence_refs", [])),
            "next_evidence_objectives": next_checks,
        }

        max_chars = int(self.limits.get("max_handoff_chars", 6000))
        while len(json.dumps(handoff, sort_keys=True)) > max_chars and handoff["next_evidence_objectives"]:
            handoff["next_evidence_objectives"].pop()
        while len(json.dumps(handoff, sort_keys=True)) > max_chars and handoff["documented_adjacency"]:
            handoff["documented_adjacency"].pop()
        while len(json.dumps(handoff, sort_keys=True)) > max_chars and handoff["accepted_evidence"]:
            handoff["accepted_evidence"][-1]["content"] = "[content omitted to preserve handoff budget]"
            if len(json.dumps(handoff, sort_keys=True)) > max_chars:
                handoff["accepted_evidence"].pop()
        if len(json.dumps(handoff, sort_keys=True)) > max_chars:
            handoff["unknowns"] = ["Additional unknowns omitted to preserve the handoff budget."]
        return handoff

    @staticmethod
    def _empty_reasoning() -> dict[str, Any]:
        return {
            "hypotheses": [],
            "information_gain": 0.0,
            "reasoning_status": "PENDING_TARGET",
            "stop_early_triggered": False,
            "conclusive_root_cause": None,
            "accepted_evidence_refs": [],
            "evidence_assessment": [],
            "next_action": "REQUEST_CLARIFICATION",
        }

    def _verification_records(
        self, target_entity_id: str, verification_result: Any
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Accept evidence only from a successful, non-simulated P2 result envelope."""
        if verification_result is None:
            return [], None
        if not isinstance(verification_result, dict):
            return [], "A malformed verification result was excluded."
        records = verification_result.get("telemetry_results")
        safety = self.policy.get("safety", {})
        allowed_adapters = set(safety.get("allowed_live_adapters", []))
        allowed_checks = set(safety.get("allowed_live_checks", []))
        max_records = int(safety.get("max_live_evidence_records", 0))
        accepted_envelope = (
            verification_result.get("status") in {"SUCCESS", "PARTIAL"}
            and verification_result.get("trust_level") == 5
            and verification_result.get("entity_id") == target_entity_id
            and verification_result.get("adapter_id") in allowed_adapters
            and verification_result.get("connection_attempted") is True
            and verification_result.get("simulation_mode") is False
            and verification_result.get("raw_output_returned") is False
            and verification_result.get("credential_returned") is False
            and verification_result.get("persistence") == "NOT_REQUESTED"
            and isinstance(records, list)
            and 0 < len(records) <= max_records
            and verification_result.get("checks_executed") == len(records)
            and all(
                isinstance(record, dict)
                and record.get("verification_check_id") in allowed_checks
                and str(record.get("source_file", "")).startswith(
                    f"live-adapter://{verification_result.get('adapter_id')}/"
                )
                for record in records
            )
        )
        if not accepted_envelope:
            return [], "A verification result lacked the required P2 provenance envelope and was excluded."
        return [record for record in records if isinstance(record, dict)], None

    def investigate(
        self,
        question: str,
        *,
        verification_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be a non-empty string")
        question = question.strip()
        if len(question) > int(self.limits.get("max_question_chars", 1000)):
            raise ValueError("question exceeds the configured character budget")

        route = self.router.classify_query(question)
        all_entities = self.entity_builder.build_index(persist=False).get("entities", [])
        resolved = self.entity_builder.resolve_entity(question) if route["requires_entity_resolution"] else []
        exact_target = resolved[0] if route["resolution_status"] == "exact" and len(resolved) == 1 else None

        if exact_target is None:
            evidence_pack = self.evidence_builder.build_evidence_pack(question, target_entities=[])
            reasoning_state = self._empty_reasoning()
            policy_state = self.policy_engine.evaluate_verification_necessity(
                route["route_type"], has_current_live_evidence=False
            )
            dependencies: list[dict[str, Any]] = []
            next_checks: list[dict[str, Any]] = []
            target_view = None
            status = "CONTEXT_ONLY" if route["resolution_status"] == "not_required" else "CLARIFICATION_REQUIRED"
        else:
            target_view = self._target_view(exact_target)
            dependencies = self._dependency_context(exact_target, all_entities)
            if (
                verification_result is not None
                and self.policy.get("safety", {}).get("allow_live_evidence_input") is not True
            ):
                supplemental_evidence = []
                verification_rejection = (
                    "A verification result was excluded because P3 policy does not accept live evidence input."
                )
            else:
                supplemental_evidence, verification_rejection = self._verification_records(
                    exact_target["entity_id"], verification_result
                )
            evidence_pack = self.evidence_builder.build_evidence_pack(
                question,
                target_entities=[exact_target],
                supplemental_evidence=supplemental_evidence,
                persist=False,
            )
            if verification_rejection:
                evidence_pack["unknowns"].append(verification_rejection)
            reasoning_state = self.reasoning.evaluate_investigation_state(
                [], evidence_pack.get("evidence_blocks", [])
            )
            has_live_evidence = bool(reasoning_state.get("accepted_evidence_refs"))
            policy_state = self.policy_engine.evaluate_verification_necessity(
                route["route_type"], has_current_live_evidence=has_live_evidence
            )
            next_checks = self._next_checks(exact_target, dependencies, reasoning_state)
            if reasoning_state["reasoning_status"] == "EVIDENCE_SUPPORTED":
                status = "EVIDENCE_SUPPORTED"
            elif reasoning_state["reasoning_status"] == "CONFLICTING_EVIDENCE":
                status = "CONFLICTING_EVIDENCE"
            else:
                status = "EVIDENCE_REQUIRED"

        handoff = self._ai_handoff(
            question,
            target_view,
            dependencies,
            evidence_pack,
            reasoning_state,
            next_checks,
        )
        handoff_chars = len(json.dumps(handoff, sort_keys=True))
        result = {
            "investigation_id": self._investigation_id(
                question, target_view["entity_id"] if target_view else "unresolved"
            ),
            "mode": self.MODE,
            "status": status,
            "question": question,
            "route": route,
            "target": target_view,
            "dependency_context": dependencies,
            "evidence_pack": evidence_pack,
            "reasoning": reasoning_state,
            "policy": policy_state,
            "next_checks": next_checks,
            "ai_handoff": handoff,
            "clarification_request": route.get("clarification_request"),
            "metrics": {
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "evidence_tokens": int(evidence_pack.get("total_tokens", 0)),
                "accepted_evidence": len(evidence_pack.get("evidence_blocks", [])),
                "unknowns": len(evidence_pack.get("unknowns", [])),
                "dependencies": len(dependencies),
                "next_checks": len(next_checks),
                "handoff_chars": handoff_chars,
            },
            "safety": {
                "live_connection_attempted": False,
                "external_ai_call_attempted": False,
                "persistence_attempted": False,
                "remediation_attempted": False,
            },
        }
        jsonschema.validate(instance=result, schema=self.schema)
        return result
