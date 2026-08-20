#!/usr/bin/env python3
"""Offline acceptance for P3 evidence-bounded incident orchestration."""

import inspect
import json
import sys
from pathlib import Path

import jsonschema
import yaml

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.api import server as api_server
from core.orchestration.incident_orchestrator import IncidentOrchestrator
from scripts.run_p3_offline_pilot import DOMAIN_SCENARIOS, run_p3_offline_pilot


def test_p3_phase() -> bool:
    print("[VALIDATING P3 OFFLINE TROUBLESHOOTING INTELLIGENCE]")
    errors: list[str] = []
    passed = 0

    policy = yaml.safe_load(
        (base_dir / "config" / "p3_troubleshooting_policy.yaml").read_text(encoding="utf-8")
    )
    safety = policy.get("safety", {})
    if (
        policy.get("mode") == "OFFLINE_NON_EXECUTING"
        and policy.get("enabled") is True
        and safety.get("require_exact_target") is True
        and safety.get("allow_live_evidence_input") is True
        and safety.get("allowed_live_adapters") == ["fortigate_ssh_readonly"]
        and safety.get("allow_live_connections") is False
        and safety.get("allow_external_ai_calls") is False
        and safety.get("allow_persistence") is False
        and safety.get("allow_remediation") is False
    ):
        print(" [PASS] P3 permits bounded evidence intake but no connection, persistence, or remediation")
        passed += 1
    else:
        errors.append("P3 policy boundary is missing or unsafe")

    orchestrator = IncidentOrchestrator(base_dir=base_dir)
    result = orchestrator.investigate("Why is fw-fortigate-hq-01 unreachable?")
    schema = json.loads(
        (base_dir / "00_meta" / "schemas" / "investigation.schema.json").read_text(encoding="utf-8")
    )
    try:
        jsonschema.validate(instance=result, schema=schema)
        schema_valid = True
    except jsonschema.ValidationError as exc:
        schema_valid = False
        errors.append(f"P3 result schema validation failed: {exc.message}")
    if schema_valid and result["status"] == "EVIDENCE_REQUIRED" and not any(result["safety"].values()):
        print(" [PASS] Investigation result is schema-valid and non-executing")
        passed += 1
    elif schema_valid:
        errors.append(f"P3 investigation truth state is invalid: {result['status']}")

    if (
        len(DOMAIN_SCENARIOS) == 7
        and result["target"]["operational_state"] == "UNKNOWN"
        and result["reasoning"]["conclusive_root_cause"] is None
        and all(item["operational_state"] == "UNKNOWN" for item in result["dependency_context"])
        and all(item["execution_state"] == "NOT_RUN" for item in result["next_checks"])
    ):
        print(" [PASS] Targets, adjacency, next checks, and current state remain truthfully separated")
        passed += 1
    else:
        errors.append("P3 context promoted documentation or plans into operational truth")

    oversized_rejected = False
    try:
        orchestrator.investigate("x" * 1001)
    except ValueError:
        oversized_rejected = True
    if oversized_rejected and result["metrics"]["handoff_chars"] <= 6000 and result["metrics"]["evidence_tokens"] <= 1500:
        print(" [PASS] Question, evidence, relationship, check, and AI-context budgets are enforced")
        passed += 1
    else:
        errors.append("P3 context budgets are not enforced")

    pilot = run_p3_offline_pilot()
    if (
        pilot["success"]
        and pilot["passed"] == pilot["total"] == 13
        and pilot["real_live_connections"] == 0
        and pilot["external_ai_calls"] == 0
        and pilot["persistence_actions"] == 0
        and pilot["remediation_actions"] == 0
    ):
        print(" [PASS] Thirteen P3 pilot scenarios preserve offline and truth boundaries")
        passed += 1
    else:
        errors.append(f"P3 pilot failed: {pilot}")

    chat_source = inspect.getsource(api_server.MNEBrainAPIHandler._handle_chat)
    if (
        "IncidentCaseManager" in chat_source
        and "detect_knowledge_drift" not in chat_source
        and '"status: ok"' not in chat_source
        and 'else "vmware"' not in chat_source
        and "execute_live_verification" not in chat_source
    ):
        print(" [PASS] Chat API delegates to P3 without platform guessing, synthetic drift, or live execution")
        passed += 1
    else:
        errors.append("Chat API retains an ad-hoc or executing investigation path")

    required = (
        base_dir / "docs" / "P3_PLAN.md",
        base_dir / "docs" / "P3_READINESS.md",
        base_dir / "docs" / "P3_OFFLINE_PILOT_REPORT.md",
        base_dir / "intelligence" / "runbooks" / "p3-ministry-incident-triage.md",
        base_dir / "00_meta" / "adr" / "ADR-009-P3-Evidence-Bounded-Incident-Orchestration.md",
    )
    ci_text = (base_dir / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    if all(path.is_file() for path in required) and "run_p3_offline_pilot.py" in ci_text:
        print(" [PASS] P3 governance, operator runbook, report, and CI entry point are present")
        passed += 1
    else:
        errors.append("P3 governance, runbook, report, or CI entry point is missing")

    print("\n--- P3 VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for error in errors:
            print(f" - {error}")
        return False
    print(f"SUCCESS: {passed} P3 Components Verified (0 Errors)")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_p3_phase() else 1)
