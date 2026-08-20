#!/usr/bin/env python3
"""Offline validation for evidence-gated diagnostic reasoning."""

import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import yaml

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.reasoning.investigation_planner import InvestigationPlanner


def _attributable_link_down_evidence() -> dict[str, object]:
    return {
        "entity_id": "test-firewall-01",
        "source_file": "operations/telemetry/ev-test-01.json",
        "source": "owner-authorized read-only test fixture",
        "evidence_status": "live_verified",
        "trust_level": 5,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "evidence_refs": ["ev-test-01"],
        "verification_target": "test-firewall-01",
        "verification_check_id": "show-interface-port1",
        "verification_outcome": "success",
        "content": "Interface port1 status down; link down.",
    }


def test_milestone_3() -> bool:
    print("[VALIDATING MILESTONE 3 REASONING ENGINE]")
    errors: list[str] = []
    passed = 0
    planner = InvestigationPlanner(certainty_threshold=0.95)

    probs_initial = [0.333, 0.333, 0.334]
    probs_focused = [0.96, 0.02, 0.02]
    info_gain = planner.calculate_information_gain(probs_initial, probs_focused)
    if planner.calculate_entropy(probs_initial) > planner.calculate_entropy(probs_focused) and info_gain > 1.0:
        print(f" [PASS] Information-gain calculation verified: {info_gain} bits")
        passed += 1
    else:
        errors.append("Information-gain calculation did not reduce entropy")

    initial_state = planner.evaluate_investigation_state([])
    if (
        initial_state["reasoning_status"] == "PENDING_EVIDENCE"
        and not initial_state["stop_early_triggered"]
        and initial_state["next_action"] == "REQUEST_POLICY_EVALUATION"
    ):
        print(" [PASS] Initial state requests policy evaluation without a conclusion")
        passed += 1
    else:
        errors.append(f"Initial evidence gate failed: {initial_state}")

    untrusted_state = planner.evaluate_investigation_state([], [{"content": "Interface status down link down"}])
    if not untrusted_state["stop_early_triggered"] and untrusted_state["accepted_evidence_refs"] == []:
        print(" [PASS] Raw incident text cannot be treated as verified telemetry")
        passed += 1
    else:
        errors.append(f"Unattributed evidence was accepted: {untrusted_state}")

    prior_hypotheses = copy.deepcopy(initial_state["hypotheses"])
    supported_state = planner.evaluate_investigation_state(
        initial_state["hypotheses"], [_attributable_link_down_evidence()]
    )
    root_cause = supported_state["conclusive_root_cause"] or {}
    if (
        supported_state["stop_early_triggered"]
        and supported_state["reasoning_status"] == "EVIDENCE_SUPPORTED"
        and supported_state["next_action"] == "RETURN_EVIDENCE_SCOPED_CONCLUSION"
        and root_cause.get("id") == "h1_interface_down"
        and initial_state["hypotheses"] == prior_hypotheses
    ):
        print(" [PASS] Attributable live evidence supports a bounded conclusion without input mutation")
        passed += 1
    else:
        errors.append(f"Evidence-gated stop-early evaluation failed: {supported_state}")

    task_file = base_dir / "tasks" / "investigate.md"
    schema_path = base_dir / "00_meta" / "schemas" / "task.schema.json"
    try:
        task_text = task_file.read_text(encoding="utf-8")
        task_data = yaml.safe_load(task_text.split("```yaml", 1)[1].split("```", 1)[0])
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(instance=task_data, schema=schema)
        print(" [PASS] Investigation task contract validates")
        passed += 1
    except (IndexError, OSError, json.JSONDecodeError, yaml.YAMLError, jsonschema.ValidationError) as exc:
        errors.append(f"Task schema validation failed: {exc}")

    print("\n--- MILESTONE 3 VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for error in errors:
            print(f" - {error}")
        return False
    print(f"SUCCESS: {passed} Reasoning Engine Components Verified (0 Errors)")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_milestone_3() else 1)
