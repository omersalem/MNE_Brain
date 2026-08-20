#!/usr/bin/env python3
"""Acceptance tests for P2 controlled read-only operationalization."""

import json
import sys
from pathlib import Path

import jsonschema
import yaml

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.verification.live_verify import LiveVerificationEngine
from core.verification.readonly_adapter import ReadOnlyVerificationAdapter
from scripts.run_p2_offline_pilot import run_p2_offline_pilot


def test_p2_phase() -> bool:
    print("[VALIDATING P2 CONTROLLED READ-ONLY OPERATIONALIZATION]")
    errors: list[str] = []
    passed = 0

    policy = yaml.safe_load(
        (base_dir / "config" / "p2_readonly_policy.yaml").read_text(encoding="utf-8")
    )
    if (
        policy["enabled"] is False
        and policy["activation_state"] == "P3_P4_SESSION_COMPLETE_POLICY_DISABLED"
        and policy["p0_containment_reference"] == "P0-SIMPLE-ENV-IGNORE-2026-08-16"
        and policy["persistence_enabled"] is False
        and policy["remediation_enabled"] is False
        and policy["target_confirmation_reference"] == "USER-CONFIRMED-EDGE-2026-08-16"
        and policy["owner_reference"] == "MNE-BRAIN-OWNER"
        and policy["owner_authorization"] == "EXPLICIT_OWNER_PROCEED"
        and policy["live_transport_adapter_reference"] == "PINNED-PLINK-FORTIGATE-EDGE-V1"
        and policy["allowed_profiles"] == ["fortigate_edge"]
    ):
        print(" [PASS] Repository P2 policy remains disabled and bounded to one profile")
        passed += 1
    else:
        errors.append(f"P2 repository policy is not fail-closed: {policy}")

    adapter_calls: list[dict] = []
    adapter = ReadOnlyVerificationAdapter(
        "fortigate_ssh_readonly",
        lambda request: adapter_calls.append(request) or {},
        simulation_mode=False,
        base_dir=base_dir,
    )
    engine = LiveVerificationEngine(
        base_dir=base_dir,
        adapters={"fortigate_ssh_readonly": adapter},
    )
    disabled = engine.execute_live_verification(
        "fortigate_edge",
        check_id="system_status",
        authorized=True,
        entity_id="fw-fortigate-edge-01",
        scope_reference="p2-review-001",
        credential_reference="secretref://fortigate/hq-readonly",
    )
    direct_bypass = adapter.collect(
        profile_name="fortigate_edge",
        platform="fortinet_fortios",
        entity_id="fw-fortigate-edge-01",
        target="192.0.2.10",
        checks=[{"check_id": "system_status", "command": "get system status"}],
        scope_reference="p2-review-001",
        credential_reference="secretref://fortigate/hq-readonly",
        timeout_seconds=10,
        max_output_bytes=65536,
        freshness_ttl_seconds=900,
        activation_context={
            "policy_enabled": True,
            "authorization_granted": True,
            "activation_state": "OFFLINE_FIXTURE_ONLY",
            "adapter_id": "fortigate_ssh_readonly",
            "entity_id": "fw-fortigate-edge-01",
            "scope_reference": "p2-review-001",
            "p0_containment_reference": None,
            "owner_reference": None,
            "owner_authorization": None,
        },
    )
    plan = engine.build_verification_plan("fortigate_edge")
    serialized_plan = json.dumps(plan)
    if (
        disabled["status"] == "NOT_CONFIGURED"
        and disabled["trust_level"] == 0
        and disabled["connection_attempted"] is False
        and not adapter_calls
        and direct_bypass["status"] == "NOT_RUN"
        and direct_bypass["reason"] == "OWNER_PROCEED_AND_LIVE_ACTIVATION_REQUIRED"
        and "get system status" not in serialized_plan
        and "get system interface physical" not in serialized_plan
        and all("command_fingerprint" in check for check in plan["planned_checks"])
    ):
        print(" [PASS] Disabled policy prevents adapter calls and redacts commands from plans")
        passed += 1
    else:
        errors.append(f"P2 disabled adapter boundary failed: result={disabled}, plan={plan}, calls={adapter_calls}")

    profile_schema = json.loads(
        (base_dir / "00_meta" / "schemas" / "profile.schema.json").read_text(encoding="utf-8")
    )
    invalid_profiles: list[str] = []
    for profile_path in sorted((base_dir / "profiles").glob("*.yaml")):
        try:
            jsonschema.validate(
                instance=yaml.safe_load(profile_path.read_text(encoding="utf-8")),
                schema=profile_schema,
            )
        except jsonschema.ValidationError as exc:
            invalid_profiles.append(f"{profile_path.name}: {exc.message}")
    if not invalid_profiles:
        print(" [PASS] Every read-only profile uses canonical entity and opaque credential references")
        passed += 1
    else:
        errors.append(f"P2 profile contract failures: {invalid_profiles}")

    pilot = run_p2_offline_pilot()
    if (
        pilot["success"]
        and pilot["passed"] == pilot["total"] == 11
        and pilot["mode"] == "OFFLINE_FIXTURE_ONLY"
        and pilot["live_connections_attempted"] == 0
        and pilot["accepted_live_evidence"] == 0
    ):
        print(" [PASS] Eleven offline pilot scenarios preserve non-connection and trust boundaries")
        passed += 1
    else:
        errors.append(f"P2 offline pilot failed: {pilot}")

    core_implementation_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            base_dir / "core" / "verification" / "live_verify.py",
            base_dir / "core" / "verification" / "readonly_adapter.py",
            base_dir / "scripts" / "run_p2_offline_pilot.py",
        )
    )
    forbidden_transport_implementations = (
        "import socket",
        "import subprocess",
        "import paramiko",
        "import requests",
        "Invoke-Command",
        "plink.exe",
    )
    transport_source = (
        base_dir / "integrations" / "fortigate" / "plink_transport.py"
    ).read_text(encoding="utf-8")
    transport_controls = (
        'TARGET = "172.23.70.4"',
        '"system_status": "get system status"',
        '"interface_stats": "get system interface physical"',
        'CREDENTIAL_REFERENCE = "secretref://local/fortigate-edge-readonly"',
        '"-hostkey"',
        '"-pwfile"',
        "TemporaryDirectory",
    )
    if (
        not any(marker in core_implementation_source for marker in forbidden_transport_implementations)
        and all(marker in transport_source for marker in transport_controls)
        and "shell=True" not in transport_source
        and "AutoAddPolicy" not in transport_source
    ):
        print(" [PASS] Core remains transport-neutral and the live adapter is pinned and exactly scoped")
        passed += 1
    else:
        errors.append("P2 transport separation or pinned-adapter controls are incomplete")

    ci_text = (base_dir / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    report_text = (base_dir / "docs" / "PRODUCTION_HARDENING_REPORT.md").read_text(encoding="utf-8")
    runbook = (base_dir / "intelligence" / "runbooks" / "p2-fortigate-readonly-pilot.md").read_text(encoding="utf-8")
    if (
        'pytest -q -p no:cacheprovider -m "offline or integration"' in ci_text
        and "INVALIDATED" in report_text
        and "P3_P4_SESSION_COMPLETE_POLICY_DISABLED" in runbook
        and "MNE-BRAIN-OWNER" in runbook
        and "explicitly says `proceed`" in runbook
    ):
        print(" [PASS] CI, status truthfulness, and operator stop conditions are enforced")
        passed += 1
    else:
        errors.append("P2 CI or documentation boundary is incomplete")

    print("\n--- P2 VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for error in errors:
            print(f" - {error}")
        return False
    print(f"SUCCESS: {passed} P2 Components Verified (0 Errors)")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_p2_phase() else 1)
