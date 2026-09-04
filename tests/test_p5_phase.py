#!/usr/bin/env python3
"""Offline acceptance for P5 runbook intelligence and coverage."""

import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import yaml
import jsonschema

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.entity.build_entity_index import EntityIndexBuilder
from core.incidents.case_manager import IncidentCaseManager
from core.runbooks.registry import RunbookRegistry
from scripts.run_p5_offline_pilot import DOMAIN_SELECTIONS, run_p5_offline_pilot


def test_p5_phase() -> bool:
    print("[VALIDATING P5 OFFLINE RUNBOOK INTELLIGENCE]")
    errors: list[str] = []
    passed = 0

    policy = yaml.safe_load(
        (base_dir / "config" / "p5_runbook_policy.yaml").read_text(encoding="utf-8")
    )
    safety = policy.get("safety", {})
    if (
        policy.get("mode") == "OWNER_REVIEWED_CONTEXT_SELECTION"
        and policy.get("owner_reference") == "MNE-BRAIN-OWNER"
        and policy.get("lifecycle", {}).get("operational_status") == "operationally_reviewed"
        and policy.get("lifecycle", {}).get("promotion_requires_owner_review") is True
        and policy.get("lifecycle", {}).get("automatic_promotion_enabled") is False
        and policy.get("lifecycle", {}).get("review_state") == "COMPLETE"
        and safety.get("include_runbook_body_in_handoff") is False
        and safety.get("allow_commands") is False
        and safety.get("allow_live_connections") is False
        and safety.get("allow_external_ai_calls") is False
        and safety.get("allow_notifications") is False
        and safety.get("allow_persistence") is False
        and safety.get("allow_remediation") is False
    ):
        print(" [PASS] P5 policy records completed sole-owner review and preserves non-execution")
        passed += 1
    else:
        errors.append("P5 policy boundary is missing or unsafe")

    registry = RunbookRegistry(base_dir=base_dir)
    index = registry.build_registry()
    if (
        index["total_runbooks"] == 12
        and len({item["runbook_id"] for item in index["runbooks"]}) == 12
        and all(item["status"] == "operationally_reviewed" for item in index["runbooks"])
        and all(item["owner_team"] == "MNE-BRAIN-OWNER" for item in index["runbooks"])
        and all(item["source_basis"] == "owner_review" for item in index["runbooks"])
        and all(item["review_sources"] for item in index["runbooks"])
        and all(item["operational_boundary"] == "PROCEDURE_REVIEWED_LIVE_STATE_UNVERIFIED" for item in index["runbooks"])
        and all(item["requires_exact_target"] is True for item in index["runbooks"])
        and all(item["live_access_allowed"] is False for item in index["runbooks"])
        and all(item["remediation_allowed"] is False for item in index["runbooks"])
    ):
        print(" [PASS] Twelve owner-reviewed runbooks satisfy the governed safety contract")
        passed += 1
    else:
        errors.append("Runbook registry count, uniqueness, or safety contract failed")

    invalid_review = deepcopy(index["runbooks"][0])
    invalid_review.pop("source_file", None)
    invalid_review["owner_team"] = "ANOTHER-APPROVER"
    rejected = False
    try:
        jsonschema.validate(invalid_review, registry.schema)
    except jsonschema.ValidationError:
        rejected = True
    if rejected:
        print(" [PASS] Runbook schema rejects any owner or approver outside the sole-owner model")
        passed += 1
    else:
        errors.append("Runbook schema accepted an obsolete multi-approver owner")

    entity_builder = EntityIndexBuilder(base_dir=base_dir)
    entities = entity_builder.build_index(persist=False)["entities"]
    coverage = registry.coverage_report(entities)
    if (
        coverage["total_entities"] == 48
        and coverage["context_covered_entities"] == 48
        and coverage["context_coverage_percent"] == 100.0
        and coverage["operationally_covered_entities"] == 48
        and coverage["operational_coverage_percent"] == 100.0
        and coverage["operational_gaps"] == []
        and coverage["operational_runbook_readiness"] is True
        and coverage["production_readiness_claimed"] is False
    ):
        print(" [PASS] All 48 entities have reviewed procedures without a production-readiness claim")
        passed += 1
    else:
        errors.append(f"Runbook coverage truthfulness failed: {coverage}")

    relevant = True
    for _, entity_id, expected in DOMAIN_SELECTIONS:
        selection = registry.select_for_target(entity_builder.resolve_entity(entity_id)[0])
        relevant = relevant and selection["candidates"][0]["runbook_id"] == expected
        relevant = relevant and selection["operational_use_allowed"] is True
        relevant = relevant and selection["selection_status"] == "OWNER_REVIEWED_GUIDANCE_AVAILABLE"
        relevant = relevant and selection["body_included"] is False
        relevant = relevant and selection["candidate_count"] <= 3
        relevant = relevant and len(json.dumps(selection, sort_keys=True)) <= 3000
    if relevant:
        print(" [PASS] Nine domain selections are relevant, deterministic, bounded, and owner-reviewed")
        passed += 1
    else:
        errors.append("Domain runbook relevance or selection budget failed")

    case = IncidentCaseManager(base_dir=base_dir).build_case(
        "Why is waf-f5-bigip-01 unavailable?",
        impact_context={
            "affected_scope": "multiple_users",
            "availability": "unavailable",
            "reported_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    guidance = case["runbook_guidance"]
    if (
        guidance["candidate_count"] == case["metrics"]["runbook_candidates"]
        and guidance["selection_status"] == "OWNER_REVIEWED_GUIDANCE_AVAILABLE"
        and guidance["operational_use_allowed"] is True
        and guidance["body_included"] is False
        and case["metrics"]["handoff_chars"] <= 8000
        and not any(case["safety"].values())
    ):
        print(" [PASS] P4 handoff includes bounded owner-reviewed P5 guidance without execution")
        passed += 1
    else:
        errors.append("P4/P5 handoff integration failed")

    pilot = run_p5_offline_pilot()
    if (
        pilot["success"]
        and pilot["passed"] == pilot["total"] == 18
        and pilot["runbooks"] == 12
        and pilot["canonical_entities"] == 48
        and pilot["context_coverage_percent"] == 100.0
        and pilot["operational_coverage_percent"] == 100.0
        and pilot["production_readiness_claimed"] is False
        and pilot["live_connections"] == 0
        and pilot["external_ai_calls"] == 0
        and pilot["notifications"] == 0
        and pilot["persistence_actions"] == 0
        and pilot["remediation_actions"] == 0
    ):
        print(" [PASS] Eighteen P5 pilot scenarios preserve owner review and non-execution boundaries")
        passed += 1
    else:
        errors.append(f"P5 pilot failed: {pilot}")

    required = (
        base_dir / "docs" / "P5_PLAN.md",
        base_dir / "docs" / "P5_READINESS.md",
        base_dir / "docs" / "P5_OFFLINE_PILOT_REPORT.md",
        base_dir / "docs" / "P5_OPERATIONAL_REVIEW_REPORT.md",
        base_dir / "docs" / "RUNBOOK_GOVERNANCE.md",
        base_dir / "00_meta" / "adr" / "ADR-011-P5-Runbook-Intelligence-and-Coverage.md",
    )
    ci_text = (base_dir / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    if all(path.is_file() for path in required) and "run_p5_offline_pilot.py" in ci_text:
        print(" [PASS] P5 plan, readiness, pilot, owner-review report, governance, ADR, and CI entry point are present")
        passed += 1
    else:
        errors.append("P5 governance or CI entry point is missing")

    print("\n--- P5 VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for error in errors:
            print(f" - {error}")
        return False
    print(f"SUCCESS: {passed} P5 Components Verified (0 Errors)")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_p5_phase() else 1)
