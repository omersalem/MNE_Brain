#!/usr/bin/env python3
"""Offline validation for planning-only remediation governance."""

import json
import io
import inspect
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import jsonschema
import yaml

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.remediation.remediation_engine import RemediationEngine
from core.api import server as api_server


def _root_cause_evidence() -> dict[str, object]:
    return {
        "reasoning_status": "EVIDENCE_SUPPORTED",
        "stop_early_triggered": True,
        "conclusive_root_cause": {"id": "test-root-cause"},
        "accepted_evidence_refs": ["ev-test-root-01"],
    }


def test_milestone_11() -> bool:
    print("[VALIDATING MILESTONE 11 CONTROLLED REMEDIATION FOUNDATION]")
    errors: list[str] = []
    passed = 0
    engine = RemediationEngine(base_dir=base_dir)

    template_files = sorted((base_dir / "actions" / "approved").glob("*.yaml"))
    invalid_templates: list[str] = []
    statuses: list[str] = []
    for template_file in template_files:
        try:
            action = engine.load_action_template(template_file.stem)
            statuses.append(action["template_status"])
        except (ValueError, jsonschema.ValidationError) as exc:
            invalid_templates.append(f"{template_file.name}: {exc}")
    if len(template_files) == 13 and not invalid_templates and set(statuses) == {"unreviewed"}:
        print(" [PASS] All 13 legacy templates validate and are explicitly unreviewed")
        passed += 1
    else:
        errors.append(f"Legacy template governance failed: count={len(template_files)}, invalid={invalid_templates}, statuses={statuses}")

    driver_calls: list[tuple[str, str]] = []

    def forbidden_driver(platform: str, command: str) -> dict[str, str]:
        driver_calls.append((platform, command))
        return {"status": "SUCCESS"}

    legacy_boolean_bypass = engine.execute_remediation(
        "level0-read-telemetry", forbidden_driver, root_cause_verified=True
    )
    level_four = engine.execute_remediation(
        "level4-emergency-firewall-change",
        forbidden_driver,
        root_cause_verified=_root_cause_evidence(),
        owner_reference="MNE-BRAIN-OWNER",
        explicit_owner_instruction=True,
    )
    if (
        legacy_boolean_bypass["status"] == "BLOCKED"
        and level_four["status"] == "BLOCKED"
        and level_four["remediation_plan"]["status"] == "CRITICAL_EXCEPTION_REQUIRED"
        and not driver_calls
    ):
        print(" [PASS] Boolean shortcuts fail and legacy Level 4 redirects to P10 without driver calls")
        passed += 1
    else:
        errors.append(f"Hard-blocking failed: legacy={legacy_boolean_bypass}, level4={level_four}, calls={driver_calls}")

    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        schema_dir = root / "00_meta" / "schemas"
        action_dir = root / "actions" / "approved"
        schema_dir.mkdir(parents=True)
        action_dir.mkdir(parents=True)
        schema_text = (base_dir / "00_meta" / "schemas" / "action.schema.json").read_text(encoding="utf-8")
        (schema_dir / "action.schema.json").write_text(schema_text, encoding="utf-8")
        hidden_marker = "hidden-command-value-must-not-appear"
        approved_action = {
            "action_id": "approved-test-change",
            "title": "Approved Offline Test Change",
            "template_status": "approved",
            "template_version": "1.0",
            "owner": "Test Team",
            "last_reviewed": "2026-08-15",
            "risk_level": 2,
            "platform": "offline-test",
            "pre_checks": ["verify_test_precondition"],
            "command": f"apply {hidden_marker}",
            "rollback_command": f"revert {hidden_marker}",
            "post_checks": ["verify_test_postcondition"],
        }
        (action_dir / "approved-test-change.yaml").write_text(
            yaml.safe_dump(approved_action, sort_keys=False), encoding="utf-8"
        )
        fixture_engine = RemediationEngine(base_dir=root)
        plan = fixture_engine.create_remediation_plan(
            "approved-test-change",
            root_cause_evidence=_root_cause_evidence(),
            owner_reference="MNE-BRAIN-OWNER",
            explicit_owner_instruction=True,
        )
        serialized_plan = json.dumps(plan)
        fixture_driver_calls: list[tuple[str, str]] = []

        def fixture_driver(platform: str, command: str) -> dict[str, str]:
            fixture_driver_calls.append((platform, command))
            return {"status": "SUCCESS"}

        execution_attempt = fixture_engine.execute_remediation(
            "approved-test-change",
            fixture_driver,
            root_cause_verified=_root_cause_evidence(),
            owner_reference="MNE-BRAIN-OWNER",
            explicit_owner_instruction=True,
        )
        if (
            plan["status"] == "READY_FOR_SEPARATE_EXECUTION_GATE"
            and plan["pre_evaluation"]["all_passed"] is True
            and plan["pre_evaluation"]["owner_reference"] == "MNE-BRAIN-OWNER"
            and plan["pre_evaluation"]["audit_mode"] == "IN_MEMORY_ONLY"
            and plan["pre_evaluation"]["retention"] == "NONE"
            and plan["execution_permitted"] is False
            and hidden_marker not in serialized_plan
            and "command" not in plan
            and "rollback_command" not in plan
            and execution_attempt["status"] == "NOT_EXECUTED"
            and execution_attempt["driver_invoked"] is False
            and not fixture_driver_calls
        ):
            print(" [PASS] Sole-owner-instructed fixtures produce in-memory redacted plans but cannot execute")
            passed += 1
        else:
            errors.append(f"Planning-only boundary failed: plan={plan}, execution={execution_attempt}, calls={fixture_driver_calls}")

    traversal = engine.create_remediation_plan("../level0-read-telemetry")
    if traversal["status"] == "BLOCKED" and traversal["execution_permitted"] is False:
        print(" [PASS] Invalid or traversal-style action identifiers fail closed")
        passed += 1
    else:
        errors.append(f"Action identifier validation failed: {traversal}")

    task_text = (base_dir / "tasks" / "remediate.md").read_text(encoding="utf-8")
    task_data = yaml.safe_load(task_text.split("```yaml", 1)[1].split("```", 1)[0])
    task_schema = json.loads((base_dir / "00_meta" / "schemas" / "task.schema.json").read_text(encoding="utf-8"))
    try:
        jsonschema.validate(instance=task_data, schema=task_schema)
        print(" [PASS] Controlled remediation planning task contract validates")
        passed += 1
    except jsonschema.ValidationError as exc:
        errors.append(f"Remediation task schema validation failed: {exc}")

    catalog_handler = object.__new__(api_server.MNEBrainAPIHandler)
    catalog_handler.wfile = io.BytesIO()
    catalog_statuses: list[int] = []
    catalog_handler._set_headers = lambda status_code=200, content_type="application/json": catalog_statuses.append(status_code)
    catalog_handler._handle_actions({})
    catalog_payload = json.loads(catalog_handler.wfile.getvalue().decode("utf-8"))
    forbidden_catalog_fields = {"command", "rollback_command", "pre_checks", "post_checks"}
    catalog_is_redacted = all(
        not forbidden_catalog_fields.intersection(action)
        and action.get("execution_permitted") is False
        for action in catalog_payload["actions"]
    )
    if catalog_statuses == [200] and catalog_payload["total_actions"] == 13 and catalog_is_redacted:
        print(" [PASS] Action catalog exposes metadata and fingerprints without command bodies")
        passed += 1
    else:
        errors.append(f"Action catalog redaction failed: statuses={catalog_statuses}, payload={catalog_payload}")

    execute_handler = object.__new__(api_server.MNEBrainAPIHandler)
    execute_handler.wfile = io.BytesIO()
    execute_statuses: list[int] = []
    execute_handler._set_headers = lambda status_code=200, content_type="application/json": execute_statuses.append(status_code)
    execute_handler._handle_action_execute(
        {
            "action_id": "level0-read-telemetry",
            "owner_reference": "MNE-BRAIN-OWNER",
            "explicit_owner_instruction": True,
        }
    )
    execute_payload = json.loads(execute_handler.wfile.getvalue().decode("utf-8"))
    execute_source = inspect.getsource(api_server.MNEBrainAPIHandler._handle_action_execute)
    if (
        execute_statuses == [409]
        and execute_payload["status"] == "BLOCKED"
        and execute_payload["driver_invoked"] is False
        and "DriverFactory" not in execute_source
        and "execute_command" not in execute_source
    ):
        print(" [PASS] Action API remains fail-closed and cannot construct a driver")
        passed += 1
    else:
        errors.append(f"Action API boundary failed: statuses={execute_statuses}, payload={execute_payload}")

    print("\n--- MILESTONE 11 VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for error in errors:
            print(f" - {error}")
        return False
    print(f"SUCCESS: {passed} Controlled Remediation Components Verified (0 Errors)")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_milestone_11() else 1)
