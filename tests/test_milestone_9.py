#!/usr/bin/env python3
"""Offline validation for non-connecting protocol-driver foundations."""

import json
import os
import sys
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.tools.drivers.driver_factory import DriverFactory


def test_milestone_9() -> bool:
    print("[VALIDATING MILESTONE 9 TOOL DRIVER FOUNDATION]")
    errors: list[str] = []
    passed = 0
    protocols = ("ssh", "rest", "powershell", "winrm", "vmware", "sql", "snmp")
    targets = {
        "ssh": "192.0.2.10",
        "rest": "https://example.invalid/api/status",
        "powershell": "localhost",
        "winrm": "192.0.2.20",
        "vmware": "vcenter.example.invalid",
        "sql": "sql.example.invalid",
        "snmp": "192.0.2.30",
    }

    factory = DriverFactory()
    plans = [factory.plan_command(protocol, targets[protocol], "read-status") for protocol in protocols]
    if all(
        plan["status"] == "PLANNED"
        and not plan["connection_attempted"]
        and plan["output"] is None
        and "operation_fingerprint" in plan
        for plan in plans
    ):
        print(" [PASS] All seven protocols produce bounded, non-connecting plans")
        passed += 1
    else:
        errors.append(f"Driver planning failed: {plans}")

    disabled_results = [
        factory.execute_command(protocol, targets[protocol], "read-status", authorized=True)
        for protocol in protocols
    ]
    if all(
        result["status"] == "EXECUTION_DISABLED"
        and not result["connection_attempted"]
        and result["output"] is None
        for result in disabled_results
    ):
        print(" [PASS] Default factory blocks every protocol before transport execution")
        passed += 1
    else:
        errors.append(f"Default execution gate failed: {disabled_results}")

    enabled_factory = DriverFactory(execution_enabled=True)
    unauthorized = enabled_factory.execute_command("ssh", "192.0.2.10", "show status")
    authorized = [
        enabled_factory.execute_command(
            protocol, targets[protocol], "read-status", authorized=True
        )
        for protocol in protocols
    ]
    if (
        unauthorized["status"] == "NOT_RUN"
        and all(
            result["status"] == "NOT_CONFIGURED"
            and not result["connection_attempted"]
            and result["output"] is None
            for result in authorized
        )
    ):
        print(" [PASS] Authorization alone cannot bypass the missing approved transport adapter")
        passed += 1
    else:
        errors.append(f"Authorized non-execution state failed: unauthorized={unauthorized}, authorized={authorized}")

    embedded_credentials = factory.plan_command(
        "rest", "https://user:password@example.invalid/api", "GET"
    )
    query_secret = factory.plan_command(
        "rest", "https://example.invalid/api?token=secret", "GET"
    )
    invalid_target = factory.plan_command("ssh", "host\nsecond-host", "show status")
    unsupported_blocked = False
    try:
        factory.get_driver("unsupported")
    except ValueError:
        unsupported_blocked = True
    if (
        embedded_credentials["status"] == "INVALID_REQUEST"
        and query_secret["status"] == "INVALID_REQUEST"
        and invalid_target["status"] == "INVALID_REQUEST"
        and unsupported_blocked
    ):
        print(" [PASS] Credential-bearing targets, malformed targets, and unknown protocols fail closed")
        passed += 1
    else:
        errors.append(
            f"Request validation failed: embedded={embedded_credentials}, query={query_secret}, invalid={invalid_target}"
        )

    secret_marker = "driver-secret-marker-must-not-appear"
    previous_secret = os.environ.get("SSH_PASSWORD")
    os.environ["SSH_PASSWORD"] = secret_marker
    try:
        redacted = factory.execute_command(
            "ssh", "192.0.2.10", f"show {secret_marker}", authorized=True
        )
        serialized = json.dumps(redacted)
    finally:
        if previous_secret is None:
            os.environ.pop("SSH_PASSWORD", None)
        else:
            os.environ["SSH_PASSWORD"] = previous_secret
    if (
        redacted["status"] == "EXECUTION_DISABLED"
        and secret_marker not in serialized
        and "command" not in redacted
        and "operation" not in redacted
    ):
        print(" [PASS] Driver responses never expose credential values or raw operations")
        passed += 1
    else:
        errors.append(f"Driver response redaction failed: {redacted}")

    print("\n--- MILESTONE 9 VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for error in errors:
            print(f" - {error}")
        return False
    print(f"SUCCESS: {passed} Tool Driver Components Verified (0 Errors)")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_milestone_9() else 1)
