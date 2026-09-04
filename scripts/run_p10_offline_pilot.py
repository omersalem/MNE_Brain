#!/usr/bin/env python3
"""Deterministic P10 multi-platform pilot with injected drivers and zero network I/O."""

from __future__ import annotations

import hashlib
import json
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.execution.p10_catalog import P10CatalogError
from core.execution.p10_engine import OWNER_REFERENCE, P10ExecutionEngine, P10SafetyError
from core.tools.drivers.p10_write import SimulatedP10WriteDriver


NOW = datetime(2026, 8, 20, 9, 0, tzinfo=timezone.utc)
PIN = "SHA256:p10-offline-pilot-identity"
DIGEST = hashlib.sha256(b"p10-offline-stable-state").hexdigest()


def evidence(engine, operation_id, binding, target, *, passed=True, facts=None):
    operation = engine.catalog.get(operation_id)
    return {
        "evidence_id": f"pilot-{operation_id}", "observed_at": engine._iso(engine._now()),
        "binding_id": binding, "target": target, "identity_pin": PIN, "state_digest": DIGEST,
        "checks": [{"check_id": check, "passed": passed, "read_only": True, "evidence_id": f"pilot-{operation_id}", "observed_at": engine._iso(engine._now())} for check in operation["pre_checks"]],
        "facts": facts or {},
    }


def prepare(engine, operation_id, binding, target):
    operation = engine.catalog.get(operation_id)
    action = operation["action_variants"][0]
    parameters = {"action": action, "resource_name": "P10_PILOT_OBJECT"}
    if operation["operation_type"] in {"address_object", "node", "network_object"}:
        parameters["value"] = "192.0.2.10/32" if operation["operation_type"] == "address_object" else "192.0.2.10"
    return engine.prepare(
        operation_id, binding_id=binding, target=target, identity_pin=PIN,
        parameters=parameters,
        evidence=evidence(engine, operation_id, binding, target),
    )


def approve(engine, plan):
    return engine.approve(plan["plan_id"], engine.expected_approval_phrase(plan["plan_id"]), owner_reference=OWNER_REFERENCE)


def probe(_plan):
    return {"identity_pin": PIN, "state_digest": DIGEST, "unrelated_pending_changes": False}


def post(_plan, _driver):
    return [{"check_id": "pilot_independent_post_check", "passed": True, "read_only": True, "evidence_id": "pilot-post", "observed_at": NOW.isoformat()}]


def critical_evidence(engine):
    return {
        "evidence_id": "pilot-critical", "observed_at": engine._iso(engine._now()),
        "binding_id": "p7-fortigate-edge", "target": "fw-pilot.invalid", "identity_pin": PIN,
        "state_digest": DIGEST, "checks": [{"check_id": "critical_scope_verified", "passed": True, "read_only": True, "evidence_id": "pilot-critical", "observed_at": engine._iso(engine._now())}], "facts": {},
    }


def warning():
    return {
        "outside_catalog_reason": "Offline pilot of an unlisted recovery action.", "expected_outcome": "Recover exact test object.",
        "blast_radius": "Exact simulated target.", "downtime_risk": "HIGH", "management_access_risk": "POSSIBLE",
        "security_risk": "HIGH", "data_loss_risk": "POSSIBLE", "dependencies_affected": "Simulated dependency.",
        "reversibility": "Separate approval.", "out_of_band_recovery": "Simulated and unavailable.",
    }


def run_pilot() -> dict:
    results = []
    drivers = []

    def scenario(name: str, callback: Callable[[], bool]):
        try:
            passed = callback() is True
            detail = "expected safety outcome observed" if passed else "callback returned false"
        except Exception as exc:
            passed, detail = False, f"{type(exc).__name__}: {exc}"
        results.append({"scenario": name, "passed": passed, "detail": detail})
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")

    platform_cases = [
        ("FortiGate", "p10-fortigate-address-object", "p7-fortigate-edge", "fw-pilot.invalid", True),
        ("F5 BIG-IP", "p10-f5-node", "p7-f5", "f5-pilot.invalid", True),
        ("FMC/FTD safe rollback gate", "p10-fmc-network-object", "p7-fmc-rest", "fmc-pilot.invalid", False),
        ("Windows PowerShell", "p10-windows-iis", "p7-ad-primary", "dc1-pilot.invalid", True),
        ("VMware", "p10-vmware-power", "p7-vcenter-rest", "vcenter-pilot.invalid", True),
        ("Cisco switching", "p10-cisco-vlan", "p7-cisco-core", "cisco-pilot.invalid", True),
        ("Fujitsu switching", "p10-fujitsu-vlan", "p7-fujitsu-sw1", "fujitsu-pilot.invalid", True),
        ("Linux", "p10-linux-service", "p7-linux-greenunit", "linux-pilot.invalid", True),
    ]
    for title, operation_id, binding, target, expects_success in platform_cases:
        def platform_success(operation_id=operation_id, binding=binding, target=target, expects_success=expects_success):
            driver = SimulatedP10WriteDriver(); drivers.append(driver)
            engine = P10ExecutionEngine(base_dir, execution_enabled=True, driver=driver, now=lambda: NOW)
            try:
                plan = prepare(engine, operation_id, binding, target)
            except (P10CatalogError, P10SafetyError) as exc:
                return not expects_success and "rollback" in str(exc).casefold() and not driver.calls
            if not expects_success:
                return False
            approve(engine, plan)
            result = engine.execute(plan["plan_id"], state_probe=probe, postcheck_runner=post)
            return result["status"] == "SUCCESS" and len(driver.calls) == 1
        scenario(f"platform {'success' if expects_success else 'safety'} - {title}", platform_success)

    def blocked_without_approval():
        driver = SimulatedP10WriteDriver(); drivers.append(driver)
        engine = P10ExecutionEngine(base_dir, execution_enabled=True, driver=driver, now=lambda: NOW)
        plan = prepare(engine, "p10-fortigate-address-object", "p7-fortigate-edge", "fw-pilot.invalid")
        try: engine.execute(plan["plan_id"], state_probe=probe, postcheck_runner=post)
        except P10SafetyError: return not driver.calls
        return False
    scenario("blocked normal execution without approval", blocked_without_approval)

    def critical(irreversible=False):
        engine = P10ExecutionEngine(base_dir, now=lambda: NOW)
        plan = engine.prepare_critical_exception(
            platform="fortinet_fortios", binding_id="p7-fortigate-edge", target="fw-pilot.invalid", identity_pin=PIN,
            commands=["execute reviewed offline recovery P10_PILOT_OBJECT"], rollback_commands=[] if irreversible else ["execute reviewed offline rollback P10_PILOT_OBJECT"],
            evidence=critical_evidence(engine), warning=warning(), irreversible=irreversible,
        )
        phrase = engine.expected_approval_phrase(plan["plan_id"])
        approve(engine, plan)
        expected = "I ACCEPT PERMANENT DATA OR SERVICE LOSS" if irreversible else "I ACCEPT THE STATED RISKS"
        return phrase.endswith(expected)
    scenario("critical exception exact approval", lambda: critical(False))
    scenario("irreversible exact approval", lambda: critical(True))

    def expired():
        clock = [NOW]
        engine = P10ExecutionEngine(base_dir, now=lambda: clock[0])
        plan = prepare(engine, "p10-fortigate-address-object", "p7-fortigate-edge", "fw-pilot.invalid")
        clock[0] += timedelta(seconds=301)
        try: approve(engine, plan)
        except P10SafetyError: return True
        return False
    scenario("expired approval", expired)

    def replay():
        engine = P10ExecutionEngine(base_dir, now=lambda: NOW); plan = prepare(engine, "p10-fortigate-address-object", "p7-fortigate-edge", "fw-pilot.invalid"); approve(engine, plan)
        try: approve(engine, plan)
        except P10SafetyError: return True
        return False
    scenario("replayed approval", replay)

    def precheck_failure():
        engine = P10ExecutionEngine(base_dir, now=lambda: NOW)
        operation_id, binding, target = "p10-fortigate-address-object", "p7-fortigate-edge", "fw-pilot.invalid"
        operation = engine.catalog.get(operation_id)
        try:
            engine.prepare(operation_id, binding_id=binding, target=target, identity_pin=PIN,
                parameters={"action": operation["action_variants"][0], "resource_name": "P10_PILOT_OBJECT", "value": "192.0.2.10/32"},
                evidence=evidence(engine, operation_id, binding, target, passed=False))
        except P10SafetyError: return True
        return False
    scenario("pre-check failure", precheck_failure)

    def postcheck_failure():
        driver = SimulatedP10WriteDriver(); drivers.append(driver)
        engine = P10ExecutionEngine(base_dir, execution_enabled=True, driver=driver, now=lambda: NOW)
        plan = prepare(engine, "p10-fortigate-address-object", "p7-fortigate-edge", "fw-pilot.invalid"); approve(engine, plan)
        result = engine.execute(plan["plan_id"], state_probe=probe, postcheck_runner=lambda p, d: [{"check_id": "post", "passed": False, "read_only": True, "evidence_id": "pilot-post-failed", "observed_at": NOW.isoformat()}])
        return result["status"] == "ROLLED_BACK_AFTER_POSTCHECK_FAILURE" and result["rollback_status"] == "VERIFIED" and not result["success"]
    scenario("declared post-check failure runs the preapproved rollback", postcheck_failure)

    def rollback_prepare():
        driver = SimulatedP10WriteDriver(); drivers.append(driver)
        engine = P10ExecutionEngine(base_dir, execution_enabled=True, driver=driver, now=lambda: NOW)
        plan = prepare(engine, "p10-fortigate-address-object", "p7-fortigate-edge", "fw-pilot.invalid"); approve(engine, plan)
        engine.execute(plan["plan_id"], state_probe=probe, postcheck_runner=post)
        rollback = engine.prepare_rollback(plan["plan_id"])
        return rollback["approval_required"] is False and rollback["rollback_hash"] == plan["rollback_hash"]
    scenario("rollback contract is covered by the original approval", rollback_prepare)

    def uncertain():
        driver = SimulatedP10WriteDriver([{"status": "TIMEOUT", "submitted": True}]); drivers.append(driver)
        engine = P10ExecutionEngine(base_dir, execution_enabled=True, driver=driver, now=lambda: NOW)
        plan = prepare(engine, "p10-fortigate-address-object", "p7-fortigate-edge", "fw-pilot.invalid"); approve(engine, plan)
        return engine.execute(plan["plan_id"], state_probe=probe, postcheck_runner=post)["status"] == "UNCERTAIN" and len(driver.calls) == 1
    scenario("uncertain execution state", uncertain)

    def injection():
        engine = P10ExecutionEngine(base_dir, now=lambda: NOW); operation = engine.catalog.get("p10-windows-service")
        try: engine.catalog.validate_parameters(operation, {"action": "restart_service", "resource_name": "DNS; Invoke-Expression bad"})
        except P10CatalogError: return True
        return False
    scenario("parameter and PowerShell injection", injection)

    def hidden_chain():
        engine = P10ExecutionEngine(base_dir, now=lambda: NOW)
        try:
            engine.prepare_critical_exception(platform="fortinet_fortios", binding_id="p7-fortigate-edge", target="fw-pilot.invalid", identity_pin=PIN,
                commands=["show safe && delete all"], rollback_commands=[], evidence=critical_evidence(engine), warning=warning())
        except P10SafetyError: return True
        return False
    scenario("hidden critical command chain", hidden_chain)

    def secret_containment():
        engine = P10ExecutionEngine(base_dir, now=lambda: NOW)
        try:
            engine.prepare_critical_exception(platform="fortinet_fortios", binding_id="p7-fortigate-edge", target="fw-pilot.invalid", identity_pin=PIN,
                commands=["set password=PilotSecret"], rollback_commands=[], evidence=critical_evidence(engine), warning=warning())
        except P10SafetyError:
            return "PilotSecret" not in json.dumps(engine.audit_records)
        return False
    scenario("secret containment", secret_containment)

    def no_safe_rollback():
        engine = P10ExecutionEngine(base_dir, now=lambda: NOW)
        plan = engine.prepare_critical_exception(platform="fortinet_fortios", binding_id="p7-fortigate-edge", target="fw-pilot.invalid", identity_pin=PIN,
            commands=["execute reviewed offline operation P10_PILOT_OBJECT"], rollback_commands=[], evidence=critical_evidence(engine), warning=warning())
        return plan["critical_warning"]["rollback"] == "NO SAFE ROLLBACK"
    scenario("NO SAFE ROLLBACK warning", no_safe_rollback)

    def concurrency():
        driver = SimulatedP10WriteDriver(); drivers.append(driver)
        engine = P10ExecutionEngine(base_dir, execution_enabled=True, driver=driver, now=lambda: NOW)
        plan = prepare(engine, "p10-fortigate-address-object", "p7-fortigate-edge", "fw-pilot.invalid"); approve(engine, plan)
        P10ExecutionEngine._global_execution_lock.acquire()
        try: result = engine.execute(plan["plan_id"], state_probe=probe, postcheck_runner=post)
        finally: P10ExecutionEngine._global_execution_lock.release()
        return result["status"] == "CONCURRENT_EXECUTION_BLOCKED" and not driver.calls
    scenario("global concurrency gate", concurrency)

    scenario("zero live connections", lambda: all(driver.live is False for driver in drivers))

    passed = sum(item["passed"] for item in results)
    report = {
        "phase": "P10", "mode": "OFFLINE_SIMULATED_ONLY", "passed": passed, "failed": len(results) - passed, "total": len(results),
        "platform_families_exercised": len(platform_cases), "live_connections": 0, "write_commands_sent_to_live_devices": 0,
        "audit_mode": "IN_MEMORY_ONLY", "retention": "NONE", "results": results,
    }
    print(f"P10 OFFLINE PILOT: {passed}/{len(results)} passed; live connections=0")
    return report


if __name__ == "__main__":
    report = run_pilot()
    sys.exit(0 if report["failed"] == 0 else 1)
