#!/usr/bin/env python3
"""Offline validation for truthful, non-executing live-verification scaffolding."""

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import jsonschema
import yaml

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.verification.live_verify import LiveVerificationEngine


def test_milestone_5() -> bool:
    print("[VALIDATING MILESTONE 5 LIVE VERIFICATION FOUNDATION]")
    errors: list[str] = []
    passed = 0
    engine = LiveVerificationEngine(base_dir=base_dir)

    fortigate_plan = engine.build_verification_plan("fortigate")
    cisco_plan = engine.build_verification_plan("cisco", check_id="ip_interface_brief")
    if (
        fortigate_plan["status"] == "PLANNED"
        and len(fortigate_plan["planned_checks"]) == 2
        and cisco_plan["planned_checks"][0]["check_id"] == "ip_interface_brief"
        and not fortigate_plan["connection_attempted"]
    ):
        print(" [PASS] Declarative profiles produce bounded, non-executing verification plans")
        passed += 1
    else:
        errors.append(f"Verification planning failed: FortiGate={fortigate_plan}, Cisco={cisco_plan}")

    unexpected_capture = base_dir / "operations" / "verification" / "fortigate_status.txt"
    capture_existed_before = unexpected_capture.exists()
    unauthorized = engine.execute_live_verification("fortigate")
    configured = engine.execute_live_verification("fortigate", authorized=True)
    if (
        unauthorized["status"] == "NOT_RUN"
        and configured["status"] == "NOT_CONFIGURED"
        and configured["trust_level"] == 0
        and configured["checks_executed"] == 0
        and not configured["connection_attempted"]
        and unexpected_capture.exists() == capture_existed_before
    ):
        print(" [PASS] Authorization or configuration never creates simulated telemetry or live trust")
        passed += 1
    else:
        errors.append(f"Non-execution safety failed: unauthorized={unauthorized}, configured={configured}")

    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        profiles = root / "profiles"
        profiles.mkdir()
        (profiles / "unsafe.yaml").write_text(
            """profile:
  platform: test
read_commands:
  - id: unsafe
    command: reboot now
""",
            encoding="utf-8",
        )
        unsafe_engine = LiveVerificationEngine(base_dir=root)
        try:
            unsafe_engine.build_verification_plan("unsafe")
            errors.append("Unsafe command was accepted as a verification plan")
        except ValueError:
            print(" [PASS] Non-read-only commands are rejected before execution")
            passed += 1

    schema = json.loads((base_dir / "00_meta" / "schemas" / "profile.schema.json").read_text(encoding="utf-8"))
    for profile_name in ("fortigate.yaml", "cisco.yaml", "vmware.yaml"):
        profile_data = yaml.safe_load((base_dir / "profiles" / profile_name).read_text(encoding="utf-8"))
        try:
            jsonschema.validate(instance=profile_data, schema=schema)
            print(f" [PASS] Profile contract validates ({profile_name})")
            passed += 1
        except jsonschema.ValidationError as exc:
            errors.append(f"Profile schema validation failed for {profile_name}: {exc}")

    print("\n--- MILESTONE 5 VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for error in errors:
            print(f" - {error}")
        return False
    print(f"SUCCESS: {passed} Live Verification Foundation Components Verified (0 Errors)")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_milestone_5() else 1)
