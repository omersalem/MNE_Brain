#!/usr/bin/env python3
"""Offline acceptance for P4 incident case management."""

import inspect
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import yaml

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.api import server as api_server
from core.incidents.case_manager import IncidentCaseManager
from scripts.run_p4_offline_pilot import run_p4_offline_pilot


def test_p4_phase() -> bool:
    print("[VALIDATING P4 OFFLINE INCIDENT OPERATIONS]")
    errors: list[str] = []
    passed = 0

    policy = yaml.safe_load(
        (base_dir / "config" / "p4_incident_policy.yaml").read_text(encoding="utf-8")
    )
    safety = policy.get("safety", {})
    governance = policy.get("workflow_governance", {})
    if (
        policy.get("mode") == "OFFLINE_CASE_MANAGEMENT"
        and safety.get("allow_reported_incident_intake") is True
        and safety.get("priority_is_provisional") is True
        and safety.get("require_owner_priority_confirmation") is True
        and safety.get("allow_live_connections") is False
        and safety.get("allow_external_ai_calls") is False
        and safety.get("allow_notifications") is False
        and safety.get("allow_persistence") is False
        and safety.get("allow_remediation") is False
        and policy.get("response_targets", {}).get("configured") is False
        and governance.get("approval_state") == "OWNER_CONTROLLED"
        and governance.get("owner_reference") == "MNE-BRAIN-OWNER"
        and governance.get("audit_mode") == "IN_MEMORY_ONLY"
        and governance.get("retention") == "NONE"
        and governance.get("ticketing_enabled") is False
        and governance.get("notifications_enabled") is False
    ):
        print(" [PASS] P4 policy permits only offline provisional case management")
        passed += 1
    else:
        errors.append("P4 policy boundary is missing or unsafe")

    manager = IncidentCaseManager(base_dir=base_dir)
    impact = {
        "affected_scope": "branch",
        "availability": "unavailable",
        "reporter_reference": "INC-P4-TEST",
        "reported_at": datetime.now(timezone.utc).isoformat(),
    }
    case = manager.build_case("Why is nablus-branch unreachable?", impact_context=impact)
    schema = json.loads(
        (base_dir / "00_meta" / "schemas" / "incident-case.schema.json").read_text(encoding="utf-8")
    )
    try:
        jsonschema.validate(instance=case, schema=schema, format_checker=jsonschema.FormatChecker())
        schema_valid = True
    except jsonschema.ValidationError as exc:
        schema_valid = False
        errors.append(f"P4 case schema validation failed: {exc.message}")
    if (
        schema_valid
        and case["priority"]["classification"] == "PROVISIONAL_P2"
        and case["impact"]["status"] == "REPORTED_NOT_VERIFIED"
        and not any(case["safety"].values())
    ):
        print(" [PASS] P4 case is schema-valid and separates reported impact from verified truth")
        passed += 1
    elif schema_valid:
        errors.append("P4 case truth or safety state is invalid")

    first_check = case["pending_checks"][0]["check_id"]
    continued = manager.build_case(
        "Why is nablus-branch unreachable?",
        impact_context=impact,
        prior_case=case,
        check_updates=[{"check_id": first_check, "status": "COLLECTED_REPORTED"}],
    )
    if (
        continued["case_id"] == case["case_id"]
        and continued["opened_at"] == case["opened_at"]
        and first_check not in {item["check_id"] for item in continued["pending_checks"]}
        and continued["check_history"][0]["verified_evidence"] is False
    ):
        print(" [PASS] Safe continuation preserves identity and avoids repeated objectives")
        passed += 1
    else:
        errors.append("P4 continuation or objective deduplication failed")

    if (
        case["ownership"]["routing_status"] == "OWNER_CONTROLLED_NOT_NOTIFIED"
        and case["ownership"]["primary"]["team"] == "MNE-BRAIN-OWNER"
        and case["response_target"]["status"] == "NO_CONFIGURED_RESPONSE_TARGET"
        and case["response_target"]["target_minutes"] is None
        and case["metrics"]["handoff_chars"] <= 8000
    ):
        print(" [PASS] Ownership, handoff, and response-target boundaries remain non-operational")
        passed += 1
    else:
        errors.append("P4 ownership, handoff, or response-target boundary failed")

    pilot = run_p4_offline_pilot()
    if (
        pilot["success"]
        and pilot["passed"] == pilot["total"] == 15
        and pilot["live_connections"] == 0
        and pilot["external_ai_calls"] == 0
        and pilot["notifications"] == 0
        and pilot["persistence_actions"] == 0
        and pilot["remediation_actions"] == 0
    ):
        print(" [PASS] Fifteen P4 pilot scenarios preserve offline case boundaries")
        passed += 1
    else:
        errors.append(f"P4 pilot failed: {pilot}")

    chat_source = inspect.getsource(api_server.MNEBrainAPIHandler._handle_chat)
    if (
        "IncidentCaseManager" in chat_source
        and 'body.get("impact_context")' in chat_source
        and 'body.get("prior_case")' in chat_source
        and 'body.get("check_updates")' in chat_source
        and "P4_INPUT_REJECTED" in chat_source
        and "execute_live_verification" not in chat_source
    ):
        print(" [PASS] Chat API delegates to P4 and rejects invalid case input without live execution")
        passed += 1
    else:
        errors.append("Chat API P4 delegation or failure boundary is incomplete")

    required = (
        base_dir / "docs" / "P4_PLAN.md",
        base_dir / "docs" / "P4_READINESS.md",
        base_dir / "docs" / "P4_OFFLINE_PILOT_REPORT.md",
        base_dir / "docs" / "P4_INCIDENT_INTAKE_REPORT.md",
        base_dir / "docs" / "P4_WORKFLOW_GOVERNANCE_REPORT.md",
        base_dir / "00_meta" / "schemas" / "incident-intake.schema.json",
        base_dir / "00_meta" / "schemas" / "incident-workflow-governance.schema.json",
        base_dir / "intelligence" / "runbooks" / "p4-incident-case-handoff.md",
        base_dir / "00_meta" / "adr" / "ADR-010-P4-Offline-Incident-Case-Management.md",
    )
    ci_text = (base_dir / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    if (
        all(path.is_file() for path in required)
        and "run_p4_offline_pilot.py" in ci_text
        and "run_p4_intake_pilot.py" in ci_text
        and "run_p4_workflow_governance_pilot.py" in ci_text
    ):
        print(" [PASS] P4 governance, runbook, report, and CI entry point are present")
        passed += 1
    else:
        errors.append("P4 governance, runbook, report, or CI entry point is missing")

    print("\n--- P4 VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for error in errors:
            print(f" - {error}")
        return False
    print(f"SUCCESS: {passed} P4 Components Verified (0 Errors)")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_p4_phase() else 1)
