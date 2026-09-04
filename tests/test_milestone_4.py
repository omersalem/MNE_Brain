#!/usr/bin/env python3
"""Offline validation for deterministic policy gates."""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.policy.policy_engine import PolicyEngine
from core.remediation.remediation_engine import RemediationEngine


def _enabled_live_policy_workspace() -> TemporaryDirectory[str]:
    temporary_directory = TemporaryDirectory()
    root = Path(temporary_directory.name)
    config_dir = root / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "action_policy.yaml").write_text(
        """live_verification:
  enabled: true
  requires_explicit_authorization: true
  reason: Test-only authorization policy.
risk_levels: {}
""",
        encoding="utf-8",
    )
    return temporary_directory


def test_milestone_4() -> bool:
    print("[VALIDATING MILESTONE 4 POLICY ENGINE]")
    errors: list[str] = []
    passed = 0
    engine = PolicyEngine(base_dir=base_dir)

    disabled_troubleshoot = engine.evaluate_verification_necessity("troubleshoot")
    if (
        disabled_troubleshoot["live_verification_required"]
        and not disabled_troubleshoot["live_verification_allowed"]
        and disabled_troubleshoot["execution_status"] == "DISABLED_BY_POLICY"
    ):
        print(" [PASS] Disabled policy blocks troubleshooting verification")
        passed += 1
    else:
        errors.append(f"Disabled verification gate failed: {disabled_troubleshoot}")

    concept = engine.evaluate_verification_necessity("concept", has_current_live_evidence=False)
    unknown_route = engine.evaluate_verification_necessity("unrecognised-route")
    if (
        not concept["live_verification_required"]
        and concept["execution_status"] == "NOT_REQUIRED"
        and unknown_route["live_verification_required"]
        and unknown_route["execution_status"] == "DISABLED_BY_POLICY"
    ):
        print(" [PASS] Concept routes bypass verification; unknown routes fail closed")
        passed += 1
    else:
        errors.append(f"Route handling failed: concept={concept}, unknown={unknown_route}")

    with _enabled_live_policy_workspace() as temporary_root:
        enabled_engine = PolicyEngine(base_dir=Path(temporary_root))
        pending = enabled_engine.evaluate_verification_necessity("troubleshoot")
        authorized = enabled_engine.evaluate_verification_necessity(
            "troubleshoot", authorization_granted=True
        )
    if (
        pending["execution_status"] == "PENDING_AUTHORIZATION"
        and not pending["live_verification_allowed"]
        and authorized["execution_status"] == "AUTHORIZED"
        and authorized["live_verification_allowed"]
    ):
        print(" [PASS] Enabled policy still requires explicit authorization")
        passed += 1
    else:
        errors.append(f"Explicit authorization gate failed: pending={pending}, authorized={authorized}")

    read_only_classification = engine.evaluate_action_policy(0)
    live_read_only = engine.evaluate_action_policy(0, is_live_verification=True)
    if (
        read_only_classification["approved"]
        and read_only_classification["policy_status"] == "READ_ONLY_CLASSIFIED"
        and not live_read_only["approved"]
        and live_read_only["policy_status"] == "DISABLED_BY_POLICY"
    ):
        print(" [PASS] Read-only classification cannot bypass the live-verification gate")
        passed += 1
    else:
        errors.append(f"Level 0 separation failed: classification={read_only_classification}, live={live_read_only}")

    level_two = engine.evaluate_action_policy(2, action_id="test-controlled-change")
    level_four = engine.evaluate_action_policy(4, action_id="test-emergency-change")
    invalid = engine.evaluate_action_policy(True)
    if (
        not level_two["approved"]
        and level_two["policy_status"] == "OWNER_INSTRUCTION_REQUIRED"
        and not level_four["approved"]
        and level_four["policy_status"] == "CRITICAL_EXCEPTION_ONLY"
        and invalid["policy_status"] == "INVALID_RISK_LEVEL"
    ):
        print(" [PASS] Sole-owner instruction, P10 critical exception routing, and risk input validation enforced")
        passed += 1
    else:
        errors.append(f"Action policy enforcement failed: L2={level_two}, L4={level_four}, invalid={invalid}")

    driver_calls: list[tuple[str, str]] = []

    def forbidden_driver(platform: str, command: str) -> dict[str, str]:
        driver_calls.append((platform, command))
        return {"status": "SUCCESS"}

    remediation_result = RemediationEngine(base_dir=base_dir).execute_remediation(
        "level0-read-telemetry", forbidden_driver
    )
    if remediation_result["status"] == "BLOCKED" and not driver_calls:
        print(" [PASS] Disabled live-verification policy prevents any remediation driver call")
        passed += 1
    else:
        errors.append(f"Remediation boundary failed: result={remediation_result}, calls={driver_calls}")

    print("\n--- MILESTONE 4 VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for error in errors:
            print(f" - {error}")
        return False
    print(f"SUCCESS: {passed} Policy Engine Components Verified (0 Errors)")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_milestone_4() else 1)
