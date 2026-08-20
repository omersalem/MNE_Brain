#!/usr/bin/env python3
"""Offline validation for the fail-closed execution state machine."""

import json
import sys
import threading
from pathlib import Path
from tempfile import TemporaryDirectory

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.execution.execution_engine import ExecutionEngine


def _action(
    action_id: str,
    *,
    risk_level: int = 0,
    command: str = "show status",
    rollback_command: str = "none",
) -> dict[str, object]:
    return {
        "action_id": action_id,
        "title": action_id,
        "platform": "offline-test",
        "command": command,
        "risk_level": risk_level,
        "pre_checks": [],
        "post_checks": [],
        "rollback_command": rollback_command,
    }


def test_milestone_8() -> bool:
    print("[VALIDATING MILESTONE 8 EXECUTION ENGINE FOUNDATION]")
    errors: list[str] = []
    passed = 0

    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        driver_calls: list[tuple[str, str]] = []

        def success_driver(platform: str, command: str) -> dict[str, str]:
            driver_calls.append((platform, command))
            return {"status": "SUCCESS", "output": "sensitive raw output"}

        disabled_engine = ExecutionEngine(base_dir=root)
        disabled = disabled_engine.execute_action(
            _action("disabled"),
            success_driver,
            owner_reference="MNE-BRAIN-OWNER",
            explicit_owner_instruction=True,
        )
        enabled_engine = ExecutionEngine(
            base_dir=root, execution_enabled=True, max_retries=2, backoff_base_seconds=0
        )
        unauthorized = enabled_engine.execute_action(
            _action("unauthorized"), success_driver, persist_audit=True
        )
        if (
            disabled["status"] == "EXECUTION_DISABLED"
            and unauthorized["status"] == "NOT_AUTHORIZED"
            and not driver_calls
            and not (root / "operations").exists()
        ):
            print(" [PASS] Disabled and unauthorized requests never invoke a driver or write audit files")
            passed += 1
        else:
            errors.append(f"Execution gate failed: disabled={disabled}, unauthorized={unauthorized}, calls={driver_calls}")

        successful = enabled_engine.execute_action(
            _action("successful"),
            success_driver,
            owner_reference="MNE-BRAIN-OWNER",
            explicit_owner_instruction=True,
        )
        if (
            successful["status"] == "SUCCESS"
            and successful["attempts"] == 1
            and len(driver_calls) == 1
            and "driver_output" not in successful
        ):
            print(" [PASS] Authorized offline callback succeeds without exposing driver output")
            passed += 1
        else:
            errors.append(f"Authorized callback handling failed: {successful}")

        retry_attempts = 0

        def transient_driver(_platform: str, _command: str) -> dict[str, str]:
            nonlocal retry_attempts
            retry_attempts += 1
            return (
                {"status": "TRANSIENT_FAILURE"}
                if retry_attempts == 1
                else {"status": "SUCCESS"}
            )

        retried = enabled_engine.execute_action(
            _action("retry-read"),
            transient_driver,
            owner_reference="MNE-BRAIN-OWNER",
            explicit_owner_instruction=True,
        )
        write_disguised_as_read = enabled_engine.execute_action(
            _action("invalid-read", command="configure terminal"),
            success_driver,
            owner_reference="MNE-BRAIN-OWNER",
            explicit_owner_instruction=True,
        )
        if (
            retried["status"] == "SUCCESS"
            and retried["attempts"] == 2
            and write_disguised_as_read["status"] == "INVALID_ACTION"
            and write_disguised_as_read["error_code"] == "READ_ONLY_ACTION_CONTAINS_WRITE_TOKEN"
        ):
            print(" [PASS] Retries are bounded to read-only actions and disguised writes are rejected")
            passed += 1
        else:
            errors.append(f"Retry/read-only enforcement failed: retry={retried}, invalid={write_disguised_as_read}")

        change_calls: list[str] = []

        def failed_change_driver(_platform: str, command: str) -> dict[str, str]:
            change_calls.append(command)
            return {"status": "FAILED", "error": "must not be audited"}

        change_result = enabled_engine.execute_action(
            _action(
                "controlled-change",
                risk_level=2,
                command="configure test value",
                rollback_command="remove test value",
            ),
            failed_change_driver,
            owner_reference="MNE-BRAIN-OWNER",
            explicit_owner_instruction=True,
        )
        if (
            change_result["status"] == "FAILED"
            and change_result["attempts"] == 1
            and change_result["rollback_status"] == "PLANNED_REQUIRES_EXPLICIT_OWNER_INSTRUCTION"
            and change_calls == ["configure test value"]
        ):
            print(" [PASS] Changes are not retried and rollback is planned rather than auto-executed")
            passed += 1
        else:
            errors.append(f"Change/rollback boundary failed: result={change_result}, calls={change_calls}")

        cancellation = threading.Event()
        cancellation.set()
        calls_before_cancel = len(driver_calls)
        cancelled = enabled_engine.execute_action(
            _action("cancelled"),
            success_driver,
            owner_reference="MNE-BRAIN-OWNER",
            explicit_owner_instruction=True,
            cancellation_event=cancellation,
        )
        timeout_engine = ExecutionEngine(
            base_dir=root, execution_enabled=True, max_retries=0, backoff_base_seconds=0
        )
        timed_out = timeout_engine.execute_action(
            _action("timeout"),
            lambda _platform, _command: {"status": "TIMEOUT"},
            owner_reference="MNE-BRAIN-OWNER",
            explicit_owner_instruction=True,
        )
        if (
            cancelled["status"] == "CANCELLED"
            and len(driver_calls) == calls_before_cancel
            and timed_out["status"] == "TIMEOUT"
            and timed_out["attempts"] == 1
        ):
            print(" [PASS] Cancellation and driver-enforced timeout states are explicit")
            passed += 1
        else:
            errors.append(f"Cancellation/timeout handling failed: cancelled={cancelled}, timeout={timed_out}")

        secret_marker = "secret-command-or-output-marker"

        def sensitive_driver(_platform: str, _command: str) -> dict[str, str]:
            return {"status": "SUCCESS", "output": secret_marker}

        persisted = enabled_engine.execute_action(
            _action("audited", command=f"show {secret_marker}"),
            sensitive_driver,
            owner_reference="MNE-BRAIN-OWNER",
            explicit_owner_instruction=True,
            persist_audit=True,
            correlation_id="corr-test-01",
        )
        audit_text = enabled_engine.audit_log_file.read_text(encoding="utf-8")
        audit_record = json.loads(audit_text.strip().splitlines()[-1])
        if (
            persisted["audit_persisted"] is True
            and audit_record["correlation_id"] == "corr-test-01"
            and secret_marker not in audit_text
            and "command" not in audit_record
            and "driver_output" not in audit_record
        ):
            print(" [PASS] Opt-in JSONL audit records are attributable and redact commands and output")
            passed += 1
        else:
            errors.append(f"Audit redaction failed: result={persisted}, record={audit_record}")

    print("\n--- MILESTONE 8 VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for error in errors:
            print(f" - {error}")
        return False
    print(f"SUCCESS: {passed} Execution Engine Components Verified (0 Errors)")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_milestone_8() else 1)
