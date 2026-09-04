#!/usr/bin/env python3
"""Offline acceptance test for the final validation and benchmark milestone."""

import sys
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))
sys.path.insert(0, str(base_dir / "tests"))

from scripts.run_benchmarks import BENCHMARK_SCENARIOS, run_benchmarks
from scripts.validate_brain import run_master_validation
from test_crash_recovery import test_crash_recovery
from test_failure_injection import run_failure_injection_suite


def test_milestone_13() -> bool:
    print("[VALIDATING MILESTONE 13 OFFLINE QUALITY GATE]")
    errors: list[str] = []
    passed = 0

    master_report = run_master_validation()
    if master_report["success"] and master_report["passed"] == master_report["total"] == 22 and master_report["mode"] == "OFFLINE_NON_EXECUTING":
        print(" [PASS] Master validation reports 22 truthful offline gates including P10 and P11")
        passed += 1
    else:
        errors.append(f"Master validation failed: {master_report}")

    benchmark_report = run_benchmarks()
    if (
        benchmark_report["success"]
        and benchmark_report["passed"] == benchmark_report["total"] == len(BENCHMARK_SCENARIOS) == 11
        and benchmark_report["mode"] == "OFFLINE_NON_EXECUTING"
        and all(result["answer_status"] == "INSUFFICIENT_EVIDENCE" for result in benchmark_report["results"])
    ):
        print(" [PASS] Eleven Ministry-domain scenarios preserve uncertainty and latency boundaries")
        passed += 1
    else:
        errors.append(f"Evidence-flow benchmarks failed: {benchmark_report}")

    source_files = [
        base_dir / "scripts" / "validate_brain.py",
        base_dir / "scripts" / "run_benchmarks.py",
        base_dir / "scripts" / "simulate_production.py",
    ]
    combined_source = "\n".join(path.read_text(encoding="utf-8") for path in source_files)
    forbidden_operations = (
        "subprocess.",
        "socket.",
        "requests.",
        "urllib.request",
        ".execute_command(",
        "persist=True",
        "external_call_allowed=True",
    )
    if not any(operation in combined_source for operation in forbidden_operations):
        print(" [PASS] Validation entry points contain no network, command, or persistence operations")
        passed += 1
    else:
        errors.append("Validation entry points contain an operation forbidden by the offline contract")

    recovery_source = (base_dir / "tests" / "test_crash_recovery.py").read_text(encoding="utf-8")
    failure_source = (base_dir / "tests" / "test_failure_injection.py").read_text(encoding="utf-8")
    unsafe_project_mutation = any(
        marker in recovery_source + failure_source
        for marker in (".unlink(", "shutil.rmtree", "base_dir / \"operations\"")
    )
    isolated_suites_pass = test_crash_recovery() and run_failure_injection_suite()
    if isolated_suites_pass and not unsafe_project_mutation:
        print(" [PASS] Recovery and failure injection use disposable, non-network fixtures")
        passed += 1
    else:
        errors.append("Recovery or failure-injection isolation failed")

    legacy_simulation = (base_dir / "scripts" / "simulate_production.py").read_text(encoding="utf-8")
    if (
        "does not simulate production" in legacy_simulation
        and "run_benchmarks" in legacy_simulation
        and "DriverFactory" not in legacy_simulation
        and "LiveVerificationEngine" not in legacy_simulation
    ):
        print(" [PASS] Legacy production-simulation entry point is explicitly offline")
        passed += 1
    else:
        errors.append("Legacy production-simulation entry point remains misleading or unsafe")

    print("\n--- MILESTONE 13 VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for error in errors:
            print(f" - {error}")
        return False
    print(f"SUCCESS: {passed} Final Validation Components Verified (0 Errors)")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_milestone_13() else 1)
