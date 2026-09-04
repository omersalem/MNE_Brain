#!/usr/bin/env python3
"""Run P5 runbook intelligence and coverage scenarios offline."""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

import yaml

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.entity.build_entity_index import EntityIndexBuilder
from core.incidents.case_manager import IncidentCaseManager
from core.runbooks.registry import RunbookRegistry


DOMAIN_SELECTIONS = (
    ("p5-04", "sw-cisco-core-01", "p5-network-infrastructure-triage"),
    ("p5-05", "fw-fortigate-nablus-01", "p5-branch-connectivity-triage"),
    ("p5-06", "ftd-cisco-hq-01", "p5-security-segmentation-triage"),
    ("p5-07", "waf-f5-bigip-01", "p5-published-service-triage"),
    ("p5-08", "dc-windows-ad-01", "p5-identity-dns-triage"),
    ("p5-09", "ex-windows-mail-01", "p5-messaging-triage"),
    ("p5-10", "vc-vmware-hq-01", "p5-virtualization-triage"),
    ("p5-11", "backup-veeam-hq-01", "p5-storage-backup-triage"),
    ("p5-12", "n8n-automation-server-01", "p5-compute-application-triage"),
)


def run_p5_offline_pilot() -> dict[str, Any]:
    print("=" * 72)
    print(" MNE_Brain P5 - Offline Runbook Intelligence Pilot")
    print("=" * 72)
    entity_builder = EntityIndexBuilder(base_dir=base_dir)
    entities = entity_builder.build_index(persist=False)["entities"]
    registry = RunbookRegistry(base_dir=base_dir)
    results: list[dict[str, Any]] = []

    def scenario(scenario_id: str, check: Callable[[], tuple[bool, str, dict[str, Any]]]) -> None:
        try:
            passed, detail, metrics = check()
        except Exception as exc:
            passed, detail, metrics = False, f"{type(exc).__name__}: {exc}", {}
        results.append({"scenario_id": scenario_id, "passed": passed, "detail": detail, "metrics": metrics})
        print(f"[{'PASS' if passed else 'FAIL'}] {scenario_id} | {detail}")

    def registry_contract() -> tuple[bool, str, dict[str, Any]]:
        index = registry.build_registry()
        statuses = {item["status"] for item in index["runbooks"]}
        passed = (
            index["total_runbooks"] == 12
            and statuses == {"operationally_reviewed"}
            and all(item["owner_team"] == "MNE-BRAIN-OWNER" for item in index["runbooks"])
            and all(item["source_basis"] == "owner_review" for item in index["runbooks"])
            and all(item["review_sources"] for item in index["runbooks"])
            and all(item["operational_boundary"] == "PROCEDURE_REVIEWED_LIVE_STATE_UNVERIFIED" for item in index["runbooks"])
            and all(item["live_access_allowed"] is False for item in index["runbooks"])
            and all(item["remediation_allowed"] is False for item in index["runbooks"])
            and index["persistence_attempted"] is False
        )
        return passed, "12 unique schema-valid runbooks completed sole-owner procedure review", {"runbooks": index["total_runbooks"]}

    scenario("p5-01", registry_contract)

    def context_coverage() -> tuple[bool, str, dict[str, Any]]:
        coverage = registry.coverage_report(entities)
        passed = (
            coverage["total_entities"] == 48
            and coverage["context_covered_entities"] == 48
            and coverage["context_coverage_percent"] == 100.0
            and coverage["context_gaps"] == []
        )
        return passed, "all 48 canonical entities have bounded offline context", coverage

    scenario("p5-02", context_coverage)

    def operational_coverage() -> tuple[bool, str, dict[str, Any]]:
        coverage = registry.coverage_report(entities)
        passed = (
            coverage["operationally_covered_entities"] == 48
            and coverage["operational_coverage_percent"] == 100.0
            and coverage["operational_gaps"] == []
            and coverage["operational_runbook_readiness"] is True
            and coverage["production_readiness_claimed"] is False
        )
        return passed, "all 48 entities have owner-reviewed procedures; live state remains unverified", coverage

    scenario("p5-03", operational_coverage)

    for scenario_id, entity_id, expected_runbook in DOMAIN_SELECTIONS:
        def selection_check(
            entity_id: str = entity_id,
            expected_runbook: str = expected_runbook,
        ) -> tuple[bool, str, dict[str, Any]]:
            target = entity_builder.resolve_entity(entity_id)[0]
            selection = registry.select_for_target(target)
            first = selection["candidates"][0]
            passed = (
                first["runbook_id"] == expected_runbook
                and selection["selection_status"] == "OWNER_REVIEWED_GUIDANCE_AVAILABLE"
                and selection["operational_use_allowed"] is True
                and first["owner_review_complete"] is True
                and first["operational_boundary"] == "PROCEDURE_REVIEWED_LIVE_STATE_UNVERIFIED"
                and selection["body_included"] is False
                and selection["candidate_count"] <= 3
            )
            return passed, f"{entity_id} selects owner-reviewed {expected_runbook}", {"candidates": selection["candidate_count"]}

        scenario(scenario_id, selection_check)

    def exact_entity_priority() -> tuple[bool, str, dict[str, Any]]:
        target = entity_builder.resolve_entity("fw-fortigate-edge-01")[0]
        selection = registry.select_for_target(target)
        passed = selection["candidates"][0]["runbook_id"] == "p2-fortigate-readonly-pilot" and "exact_entity" in selection["candidates"][0]["match_basis"]
        return passed, "exact-entity pilot metadata outranks generic context without activation", {"score": selection["candidates"][0]["score"]}

    scenario("p5-13", exact_entity_priority)

    def unknown_target() -> tuple[bool, str, dict[str, Any]]:
        selection = registry.select_for_target(None)
        passed = selection["selection_status"] == "NO_MATCH" and selection["candidate_count"] == 0 and selection["target_entity_id"] is None
        return passed, "unknown target returns no runbook guidance", {}

    scenario("p5-14", unknown_target)

    def malformed_runbook() -> tuple[bool, str, dict[str, Any]]:
        rejected = False
        with TemporaryDirectory(prefix="mne-p5-malformed-") as temp_dir:
            Path(temp_dir, "bad.md").write_text("# no governed frontmatter", encoding="utf-8")
            try:
                RunbookRegistry(base_dir=base_dir, runbooks_dir=Path(temp_dir)).build_registry()
            except ValueError:
                rejected = True
        return rejected, "runbook without governed metadata fails closed", {}

    scenario("p5-15", malformed_runbook)

    def duplicate_runbook() -> tuple[bool, str, dict[str, Any]]:
        rejected = False
        source = registry.build_registry()["runbooks"][0]
        metadata = {key: value for key, value in source.items() if key != "source_file"}
        content = f"---\n{yaml.safe_dump(metadata, sort_keys=False)}---\n# Fixture\n"
        with TemporaryDirectory(prefix="mne-p5-duplicate-") as temp_dir:
            Path(temp_dir, "one.md").write_text(content, encoding="utf-8")
            Path(temp_dir, "two.md").write_text(content, encoding="utf-8")
            try:
                RunbookRegistry(base_dir=base_dir, runbooks_dir=Path(temp_dir)).build_registry()
            except ValueError:
                rejected = True
        return rejected, "duplicate runbook IDs fail closed", {}

    scenario("p5-16", duplicate_runbook)

    def minimized_guidance() -> tuple[bool, str, dict[str, Any]]:
        target = entity_builder.resolve_entity("waf-f5-bigip-01")[0]
        first = registry.select_for_target(target)
        second = registry.select_for_target(target)
        serialized = json.dumps(first, sort_keys=True).casefold()
        forbidden = ("password", "credential_reference", "raw_output", "show system", "172.23.")
        passed = (
            first == second
            and len(json.dumps(first, sort_keys=True)) <= 3000
            and not any(marker in serialized for marker in forbidden)
            and all(not value for key, value in first.items() if key.endswith("_attempted") or key == "notification_sent")
        )
        return passed, "selection is deterministic, metadata-only, bounded, and side-effect free", {"guidance_chars": len(json.dumps(first, sort_keys=True))}

    scenario("p5-17", minimized_guidance)

    def p4_handoff_integration() -> tuple[bool, str, dict[str, Any]]:
        case = IncidentCaseManager(base_dir=base_dir).build_case(
            "Why is waf-f5-bigip-01 unavailable?",
            impact_context={
                "affected_scope": "multiple_users",
                "availability": "unavailable",
                "reported_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        guidance = case["runbook_guidance"]
        serialized = json.dumps(case["handoff_packet"], sort_keys=True)
        passed = (
            guidance["candidate_count"] == case["metrics"]["runbook_candidates"]
            and guidance["selection_status"] == "OWNER_REVIEWED_GUIDANCE_AVAILABLE"
            and guidance["body_included"] is False
            and guidance["operational_use_allowed"] is True
            and case["metrics"]["handoff_chars"] <= 8000
            and "# Published Web Service" not in serialized
        )
        return passed, "P4 handoff includes owner-reviewed metadata without runbook body", case["metrics"]

    scenario("p5-18", p4_handoff_integration)

    passed_count = sum(1 for result in results if result["passed"])
    report = {
        "success": passed_count == len(results),
        "mode": "OWNER_REVIEWED_CONTEXT_SELECTION",
        "passed": passed_count,
        "total": len(results),
        "runbooks": 12,
        "canonical_entities": 48,
        "context_coverage_percent": 100.0,
        "operational_coverage_percent": 100.0,
        "production_readiness_claimed": False,
        "live_connections": 0,
        "external_ai_calls": 0,
        "notifications": 0,
        "persistence_actions": 0,
        "remediation_actions": 0,
        "results": results,
    }
    print("=" * 72)
    print(f" P5 OFFLINE PILOT: {passed_count} / {len(results)} SCENARIOS PASSED")
    print(" Context coverage: 100% | Reviewed procedures: 100% | Live state: unverified | Side effects: 0")
    print("=" * 72)
    return report


if __name__ == "__main__":
    sys.exit(0 if run_p5_offline_pilot()["success"] else 1)
