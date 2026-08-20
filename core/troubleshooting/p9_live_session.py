"""Adaptive P9 session coordinator with an optional injected AI reasoning boundary."""

from pathlib import Path
from typing import Any, Callable

from core.troubleshooting.p9_engine import P9DiagnosticEngine


class P9LiveSession:
    def __init__(self, base_dir: Path, collector: Callable[..., dict[str, Any]], reasoning_provider: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None):
        self.engine = P9DiagnosticEngine(base_dir)
        self.collector = collector
        self.reasoning_provider = reasoning_provider

    def run(self, request: dict[str, Any], *, owner_proceed: bool) -> dict[str, Any]:
        base_request = {key: request.get(key) for key in ("scenario_id", "binding_id", "symptom")}
        plan = self.engine.plan(base_request)
        if not owner_proceed:
            return {"status": "NOT_RUN", "reason": "OWNER_PROCEED_REQUIRED", "plan": plan, "collection_results": [], "connection_attempted": False}
        evidence: list[dict[str, Any]] = []
        attempts: list[dict[str, Any]] = []
        attempted_ids: set[str] = set()
        assessment = None
        limit = int(self.engine.policy["maximum_checks_per_session"])
        while len(attempts) < limit:
            state = self.engine.plan({**base_request, "evidence": evidence, "reasoning_assessment": assessment})
            if state["stop_early"]:
                break
            next_check = next((item for item in state["candidate_checks"] if item["check_id"] not in attempted_ids), None)
            if next_check is None:
                break
            attempted_ids.add(next_check["check_id"])
            collected = self.collector(scenario_id=str(base_request["scenario_id"]), primary_binding=str(base_request["binding_id"]), check_id=next_check["check_id"], owner_proceed=True)
            attempts.append({key: collected.get(key) for key in ("status", "binding_id", "check_id", "connection_attempted")})
            if collected.get("evidence"):
                evidence.append(collected["evidence"])
            if self.reasoning_provider and evidence:
                probe = self.engine.plan({**base_request, "evidence": evidence})
                assessment = self.reasoning_provider(probe["ai_handoff"])
        final = self.engine.plan({**base_request, "evidence": evidence, "reasoning_assessment": assessment})
        final["collection_results"] = attempts
        failed_checks = [item["check_id"] for item in attempts if item.get("status") != "SUCCESS"]
        final["failed_checks"] = failed_checks
        if failed_checks and not final["stop_early"]:
            final["status"] = "PARTIAL_EVIDENCE_COLLECTION_FAILED"
            final["action"] = "REVIEW_FAILED_CHECK_OR_SELECT_SAFE_ALTERNATIVE"
        connection_attempted = any(item.get("connection_attempted") for item in attempts)
        final["safety"]["live_connection_attempted"] = connection_attempted
        final["live_session"] = {
            "status": "COMPLETE", "owner_reference": "MNE-BRAIN-OWNER",
            "connection_attempted": connection_attempted,
            "raw_output_included": False, "credentials_returned": False,
            "persistence_attempted": False, "external_ai_call_attempted": False,
            "remediation_attempted": False, "notifications_sent": False,
            "policy_restored_to_disabled": True,
        }
        return final
