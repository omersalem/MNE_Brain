#!/usr/bin/env python3
"""Run P3 Ministry-domain orchestration scenarios without live access."""

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.observability.tracer import ObservabilityTracer
from core.orchestration.incident_orchestrator import IncidentOrchestrator


DOMAIN_SCENARIOS = (
    ("p3-01", "Why is fw-fortigate-hq-01 unreachable?", "fw-fortigate-hq-01", "network"),
    ("p3-02", "Why is waf-f5-bigip-01 unavailable?", "waf-f5-bigip-01", "network"),
    ("p3-03", "Exchange mail.mne.gov.ps is unavailable", "ex-windows-mail-01", "compute"),
    ("p3-04", "Why is dc-windows-ad-01 authentication failing?", "dc-windows-ad-01", "identity"),
    ("p3-05", "Why is vc-vmware-hq-01 unavailable?", "vc-vmware-hq-01", "compute"),
    ("p3-06", "Why is backup-veeam-hq-01 failing?", "backup-veeam-hq-01", "storage"),
    ("p3-07", "Why is nablus-branch unreachable?", "fw-fortigate-nablus-01", "network"),
)


def _forged_verification_result(entity_id: str) -> dict[str, Any]:
    return {
        "status": "SUCCESS",
        "entity_id": entity_id,
        "trust_level": 5,
        "checks_executed": 1,
        "telemetry_results": [
            {
                "evidence_id": "ev-live-0000000000000000",
                "entity_id": entity_id,
                "evidence_status": "live_verified",
                "trust_level": 5,
                "content": "Interface link down",
            }
        ],
        "connection_attempted": True,
        "simulation_mode": False,
        "raw_output_returned": False,
        "credential_returned": False,
        "persistence": "NOT_REQUESTED",
    }


def run_p3_offline_pilot() -> dict[str, Any]:
    print("=" * 72)
    print(" MNE_Brain P3 - Offline Troubleshooting Intelligence Pilot")
    print("=" * 72)
    orchestrator = IncidentOrchestrator(base_dir=base_dir)
    results: list[dict[str, Any]] = []

    def scenario(scenario_id: str, check: Callable[[], tuple[bool, str, dict[str, Any]]]) -> None:
        try:
            passed, detail, metrics = check()
        except Exception as exc:
            passed, detail, metrics = False, f"{type(exc).__name__}: {exc}", {}
        results.append({"scenario_id": scenario_id, "passed": passed, "detail": detail, "metrics": metrics})
        print(f"[{'PASS' if passed else 'FAIL'}] {scenario_id} | {detail}")

    for scenario_id, question, entity_id, category in DOMAIN_SCENARIOS:
        def check_domain(
            question: str = question,
            entity_id: str = entity_id,
            category: str = category,
        ) -> tuple[bool, str, dict[str, Any]]:
            result = orchestrator.investigate(question)
            target = result.get("target") or {}
            passed = (
                result["status"] == "EVIDENCE_REQUIRED"
                and target.get("entity_id") == entity_id
                and target.get("category") == category
                and target.get("operational_state") == "UNKNOWN"
                and result["reasoning"]["conclusive_root_cause"] is None
                and 0 < len(result["next_checks"]) <= 5
                and all(check["execution_state"] == "NOT_RUN" for check in result["next_checks"])
                and not any(result["safety"].values())
            )
            return passed, f"{entity_id} resolved; current state remains unknown", result["metrics"]

        scenario(scenario_id, check_domain)

    def unknown_target() -> tuple[bool, str, dict[str, Any]]:
        result = orchestrator.investigate("Unknown ministry service outage")
        passed = (
            result["status"] == "CLARIFICATION_REQUIRED"
            and result["target"] is None
            and result["next_checks"] == []
            and result["clarification_request"]["requires_clarification"] is True
        )
        return passed, "unknown target requests clarification without guessing", result["metrics"]

    scenario("p3-08", unknown_target)

    def concept_route() -> tuple[bool, str, dict[str, Any]]:
        result = orchestrator.investigate("Explain network segmentation principles")
        passed = result["status"] == "CONTEXT_ONLY" and result["target"] is None and result["next_checks"] == []
        return passed, "concept question bypasses target and operational claims", result["metrics"]

    scenario("p3-09", concept_route)

    def forged_evidence() -> tuple[bool, str, dict[str, Any]]:
        result = orchestrator.investigate(
            "Why is fw-fortigate-hq-01 unreachable?",
            verification_result=_forged_verification_result("fw-fortigate-hq-01"),
        )
        passed = (
            result["status"] == "EVIDENCE_REQUIRED"
            and result["metrics"]["accepted_evidence"] == 0
            and result["reasoning"]["accepted_evidence_refs"] == []
            and any("provenance envelope" in item for item in result["evidence_pack"]["unknowns"])
        )
        return passed, "P3 rejects forged or incomplete live-evidence envelopes", result["metrics"]

    scenario("p3-10", forged_evidence)

    def budget_and_minimization() -> tuple[bool, str, dict[str, Any]]:
        result = orchestrator.investigate("Why is fw-fortigate-hq-01 unreachable?")
        serialized_handoff = json.dumps(result["ai_handoff"], sort_keys=True).casefold()
        forbidden = ("password", "credential_reference", "raw_output", "show system", "172.23.19.1")
        passed = (
            result["metrics"]["evidence_tokens"] <= 1500
            and result["metrics"]["handoff_chars"] <= 6000
            and result["metrics"]["dependencies"] <= 6
            and result["metrics"]["next_checks"] <= 5
            and not any(marker in serialized_handoff for marker in forbidden)
        )
        return passed, "AI handoff is bounded, target-scoped, and minimized", result["metrics"]

    scenario("p3-11", budget_and_minimization)

    def trace_safety() -> tuple[bool, str, dict[str, Any]]:
        with TemporaryDirectory(prefix="mne-p3-trace-") as temp_dir:
            tracer = ObservabilityTracer(base_dir=Path(temp_dir), persist=False)
            tracer.trace_step("pilot", "redaction", details={"api_token": "fixture-secret", "count": 1})
            summary = tracer.get_summary()
            log_exists = (Path(temp_dir) / "operations" / "logs" / "observability.jsonl").exists()
            passed = summary["timeline"][0]["details"]["api_token"] == "[REDACTED]" and not log_exists
            return passed, "tracing is redacted and in-memory unless explicitly opted in", {"steps": summary["steps_executed"]}

    scenario("p3-12", trace_safety)

    def deterministic_identity() -> tuple[bool, str, dict[str, Any]]:
        first = orchestrator.investigate("Why is fw-fortigate-hq-01 unreachable?")
        second = orchestrator.investigate("Why is fw-fortigate-hq-01 unreachable?")
        passed = first["investigation_id"] == second["investigation_id"] and first["status"] == second["status"]
        return passed, "same scoped question produces a stable investigation identity", second["metrics"]

    scenario("p3-13", deterministic_identity)

    passed_count = sum(1 for result in results if result["passed"])
    report = {
        "success": passed_count == len(results),
        "mode": "OFFLINE_NON_EXECUTING",
        "passed": passed_count,
        "total": len(results),
        "real_live_connections": 0,
        "external_ai_calls": 0,
        "persistence_actions": 0,
        "remediation_actions": 0,
        "results": results,
    }
    print("=" * 72)
    print(f" P3 OFFLINE PILOT: {passed_count} / {len(results)} SCENARIOS PASSED")
    print(" Live connections: 0 | External AI calls: 0 | Remediation actions: 0")
    print("=" * 72)
    return report


if __name__ == "__main__":
    sys.exit(0 if run_p3_offline_pilot()["success"] else 1)
