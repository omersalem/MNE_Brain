#!/usr/bin/env python3
"""Run P4 offline incident-operations acceptance scenarios."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.incidents.case_manager import IncidentCaseManager


def _impact(scope: str, availability: str, **extra: Any) -> dict[str, Any]:
    return {
        "affected_scope": scope,
        "availability": availability,
        "reporter_reference": "INC-P4-PILOT",
        "reported_at": datetime.now(timezone.utc).isoformat(),
        **extra,
    }


def run_p4_offline_pilot() -> dict[str, Any]:
    print("=" * 72)
    print(" MNE_Brain P4 - Offline Incident Operations Pilot")
    print("=" * 72)
    manager = IncidentCaseManager(base_dir=base_dir)
    results: list[dict[str, Any]] = []

    def scenario(scenario_id: str, check: Callable[[], tuple[bool, str, dict[str, Any]]]) -> None:
        try:
            passed, detail, metrics = check()
        except Exception as exc:
            passed, detail, metrics = False, f"{type(exc).__name__}: {exc}", {}
        results.append({"scenario_id": scenario_id, "passed": passed, "detail": detail, "metrics": metrics})
        print(f"[{'PASS' if passed else 'FAIL'}] {scenario_id} | {detail}")

    def missing_impact() -> tuple[bool, str, dict[str, Any]]:
        case = manager.build_case("Why is fw-fortigate-hq-01 unreachable?")
        passed = case["case_state"] == "IMPACT_REQUIRED" and case["priority"]["classification"] == "UNASSESSED"
        return passed, "missing impact remains unassessed", case["metrics"]

    scenario("p4-01", missing_impact)

    priority_cases = (
        ("p4-02", "Why is ex-windows-mail-01 unavailable?", _impact("single_user", "unavailable"), "PROVISIONAL_P3"),
        ("p4-03", "Why is nablus-branch unreachable?", _impact("branch", "unavailable"), "PROVISIONAL_P2"),
        ("p4-04", "Why is dc-windows-ad-01 degraded?", _impact("ministry_wide", "degraded"), "PROVISIONAL_P1"),
        (
            "p4-05",
            "Why is waf-f5-bigip-01 unavailable?",
            _impact("unknown", "unknown", security_impact_reported=True),
            "PROVISIONAL_P1",
        ),
        (
            "p4-06",
            "Why is waf-f5-bigip-01 unavailable?",
            _impact("multiple_users", "unavailable", public_service_reported=True),
            "PROVISIONAL_P2",
        ),
    )
    for scenario_id, question, impact, expected_priority in priority_cases:
        def priority_check(
            question: str = question,
            impact: dict[str, Any] = impact,
            expected_priority: str = expected_priority,
        ) -> tuple[bool, str, dict[str, Any]]:
            case = manager.build_case(question, impact_context=impact)
            passed = (
                case["priority"]["classification"] == expected_priority
                and case["priority"]["basis"] == "REPORTED_IMPACT_ONLY"
                and case["priority"]["owner_confirmation_required"] is True
                and case["safety"]["reported_impact_verified"] is False
                and case["safety"]["priority_confirmed"] is False
            )
            return passed, f"reported impact maps to {expected_priority} pending owner confirmation", case["metrics"]

        scenario(scenario_id, priority_check)

    def unknown_target() -> tuple[bool, str, dict[str, Any]]:
        case = manager.build_case("Unknown ministry application outage", impact_context=_impact("multiple_users", "unavailable"))
        passed = case["case_state"] == "NEEDS_TARGET" and case["target"] is None and case["metrics"]["owner_routes"] == 0
        return passed, "unknown target blocks ownership and evidence routing", case["metrics"]

    scenario("p4-07", unknown_target)

    def ownership() -> tuple[bool, str, dict[str, Any]]:
        case = manager.build_case("Why is vc-vmware-hq-01 unavailable?", impact_context=_impact("multiple_users", "unavailable"))
        owner = case["ownership"]
        passed = (
            owner["primary"]["team"] == "MNE-BRAIN-OWNER"
            and owner["routing_status"] == "OWNER_CONTROLLED_NOT_NOTIFIED"
            and owner["primary"]["notification_sent"] is False
            and all(item["notification_sent"] is False for item in owner["supporting"])
        )
        return passed, "sole owner controls the case without notification", case["metrics"]

    scenario("p4-08", ownership)

    def continuation_dedup() -> tuple[bool, str, dict[str, Any]]:
        impact = _impact("branch", "unavailable")
        first = manager.build_case("Why is nablus-branch unreachable?", impact_context=impact)
        completed_id = first["pending_checks"][0]["check_id"]
        second = manager.build_case(
            "Why is nablus-branch unreachable?",
            prior_case=first,
            check_updates=[
                {
                    "check_id": completed_id,
                    "status": "COLLECTED_REPORTED",
                    "reference_ids": ["OBS-P4-001"],
                }
            ],
        )
        passed = (
            second["case_id"] == first["case_id"]
            and second["opened_at"] == first["opened_at"]
            and second["impact"] == first["impact"]
            and second["priority"] == first["priority"]
            and completed_id not in {item["check_id"] for item in second["pending_checks"]}
            and second["check_history"][0]["verified_evidence"] is False
        )
        return passed, "continuation preserves identity and suppresses a reported-completed objective", second["metrics"]

    scenario("p4-09", continuation_dedup)

    def failed_check_review() -> tuple[bool, str, dict[str, Any]]:
        impact = _impact("multiple_users", "unavailable")
        first = manager.build_case("Why is backup-veeam-hq-01 failing?", impact_context=impact)
        failed_id = first["pending_checks"][0]["check_id"]
        second = manager.build_case(
            "Why is backup-veeam-hq-01 failing?",
            impact_context=impact,
            prior_case=first,
            check_updates=[{"check_id": failed_id, "status": "FAILED_REPORTED"}],
        )
        pending = {item["check_id"]: item for item in second["pending_checks"]}
        passed = failed_id in pending and pending[failed_id]["requires_review_before_retry"] is True
        return passed, "failed objective remains visible and requires review before retry", second["metrics"]

    scenario("p4-10", failed_check_review)

    def mismatch_rejected() -> tuple[bool, str, dict[str, Any]]:
        first = manager.build_case("Why is fw-fortigate-hq-01 unreachable?", impact_context=_impact("multiple_users", "unavailable"))
        rejected = False
        try:
            manager.build_case(
                "Why is vc-vmware-hq-01 unavailable?",
                impact_context=_impact("multiple_users", "unavailable"),
                prior_case=first,
            )
        except ValueError:
            rejected = True
        return rejected, "cross-target case continuation fails closed", {}

    scenario("p4-11", mismatch_rejected)

    def malformed_impact() -> tuple[bool, str, dict[str, Any]]:
        rejected = False
        try:
            manager.build_case(
                "Why is fw-fortigate-hq-01 unreachable?",
                impact_context={"affected_scope": "everyone", "availability": "catastrophic"},
            )
        except ValueError:
            rejected = True
        return rejected, "impact values outside the allowlist fail closed", {}

    scenario("p4-12", malformed_impact)

    def future_report() -> tuple[bool, str, dict[str, Any]]:
        rejected = False
        impact = _impact("multiple_users", "unavailable")
        impact["reported_at"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        try:
            manager.build_case("Why is fw-fortigate-hq-01 unreachable?", impact_context=impact)
        except ValueError:
            rejected = True
        return rejected, "future impact timestamps fail closed", {}

    scenario("p4-13", future_report)

    def handoff_budget() -> tuple[bool, str, dict[str, Any]]:
        case = manager.build_case("Why is waf-f5-bigip-01 unavailable?", impact_context=_impact("multiple_users", "unavailable"))
        serialized = json.dumps(case["handoff_packet"], sort_keys=True).casefold()
        forbidden = ("password", "credential_reference", "raw_output", "show system", "172.23.")
        passed = case["metrics"]["handoff_chars"] <= 8000 and not any(item in serialized for item in forbidden)
        return passed, "handoff is bounded and excludes secrets, commands, raw output, and IPs", case["metrics"]

    scenario("p4-14", handoff_budget)

    def no_sla_or_side_effects() -> tuple[bool, str, dict[str, Any]]:
        case = manager.build_case("Why is dc-windows-ad-01 degraded?", impact_context=_impact("ministry_wide", "degraded"))
        passed = (
            case["response_target"]["status"] == "NO_CONFIGURED_RESPONSE_TARGET"
            and case["response_target"]["target_minutes"] is None
            and not any(case["safety"].values())
        )
        return passed, "no SLA, notification, persistence, live access, or remediation is invented", case["metrics"]

    scenario("p4-15", no_sla_or_side_effects)

    passed_count = sum(1 for result in results if result["passed"])
    report = {
        "success": passed_count == len(results),
        "mode": "OFFLINE_CASE_MANAGEMENT",
        "passed": passed_count,
        "total": len(results),
        "live_connections": 0,
        "external_ai_calls": 0,
        "notifications": 0,
        "persistence_actions": 0,
        "remediation_actions": 0,
        "results": results,
    }
    print("=" * 72)
    print(f" P4 OFFLINE PILOT: {passed_count} / {len(results)} SCENARIOS PASSED")
    print(" Live: 0 | AI calls: 0 | Notifications: 0 | Persistence: 0 | Remediation: 0")
    print("=" * 72)
    return report


if __name__ == "__main__":
    sys.exit(0 if run_p4_offline_pilot()["success"] else 1)
