"""Regression coverage for the loopback-only Owner Full Control contract."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.execution.p10_engine import OWNER_REFERENCE, P10ExecutionEngine, P10SafetyError
from core.infrastructure.coverage import InfrastructureCoverageService
from core.tools.broker import ToolBroker
from core.tools.drivers.p10_write import SimulatedP10WriteDriver


BASE = Path(__file__).resolve().parent.parent
SESSION_A = "a" * 64
SESSION_B = "b" * 64


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _plan(engine: P10ExecutionEngine, *, session: str = SESSION_A) -> dict:
    operation = engine.catalog.get("p10-fortigate-address-object")
    observed = engine._iso(engine._now())
    evidence = {
        "evidence_id": "ev-owner-full-control-fixture",
        "observed_at": observed,
        "binding_id": "p7-fortigate-edge",
        "target": "fw.example.invalid",
        "identity_pin": "SHA256:fixture-identity",
        "state_digest": _digest("baseline"),
        "checks": [
            {"check_id": check, "passed": True, "read_only": True,
             "evidence_id": "ev-owner-full-control-fixture", "observed_at": observed}
            for check in operation["pre_checks"]
        ],
        "facts": {},
    }
    return engine.prepare(
        "p10-fortigate-address-object", binding_id="p7-fortigate-edge",
        target="fw.example.invalid", identity_pin="SHA256:fixture-identity",
        parameters={"action": "create_address", "resource_name": "OWNER_FULL_CONTROL_TEST", "value": "192.0.2.10"},
        evidence=evidence, owner_session_digest=session,
    )


def _probe(_plan: dict) -> dict:
    return {"identity_pin": "SHA256:fixture-identity", "state_digest": _digest("baseline"), "unrelated_pending_changes": False}


def test_owner_full_control_coverage_includes_every_canonical_entity_without_values():
    report = InfrastructureCoverageService(BASE).status()
    serialized = json.dumps(report, sort_keys=True)
    assert report["mode"] == "OWNER_FULL_CONTROL"
    assert report["total_entities"] == len(report["entities"]) == 48
    assert sum(report["coverage_counts"].values()) == 48
    assert report["engine_capabilities"]["parity"] is True
    assert report["secrets_returned"] is False and report["connection_attempted"] is False
    assert "credential_value" not in serialized and "password" not in serialized.casefold()


def test_protocol_target_selection_uses_kerberos_fqdn_and_exact_switch_target_without_connection():
    broker = ToolBroker(BASE, p7_scoped_available=True)
    ad = broker.live_read_arguments_for_entity("dc-mne-ad-01")
    tulkarm = broker.live_read_arguments_for_entity("sw-cisco-tulkarm-01")
    assert ad == {"binding_id": "p7-ad-primary", "target": "MNE-DC1.mne.gov", "check_id": "identity_services"}
    assert tulkarm == {"binding_id": "p7-switch-tulkarm", "target": "10.165.18.3", "check_id": "ip_interface_brief"}


def test_single_approval_is_session_bound_and_covers_declared_automatic_rollback():
    driver = SimulatedP10WriteDriver([
        {"status": "SUBMITTED", "submitted": True},
        {"status": "COMMITTED", "submitted": True},
    ])
    engine = P10ExecutionEngine(BASE, execution_enabled=True, driver=driver)
    plan = _plan(engine)
    assert "owner_session_digest" not in plan
    with pytest.raises(P10SafetyError, match="different owner session"):
        engine.approve(plan["plan_id"], engine.expected_approval_phrase(plan["plan_id"]), owner_reference=OWNER_REFERENCE, owner_session_digest=SESSION_B)
    engine.approve(plan["plan_id"], engine.expected_approval_phrase(plan["plan_id"]), owner_reference=OWNER_REFERENCE, owner_session_digest=SESSION_A)
    with pytest.raises(P10SafetyError, match="different owner session"):
        engine.execute(plan["plan_id"], owner_session_digest=SESSION_B, state_probe=_probe, postcheck_runner=lambda *_: [])
    result = engine.execute(
        plan["plan_id"], owner_session_digest=SESSION_A, state_probe=_probe,
        postcheck_runner=lambda *_: [{
            "check_id": "independent_post_check", "passed": False, "read_only": True,
            "evidence_id": "ev-postcheck-failed", "observed_at": datetime.now(timezone.utc).isoformat(),
        }],
    )
    assert result["status"] == "ROLLED_BACK_AFTER_POSTCHECK_FAILURE"
    assert result["rollback_status"] == "VERIFIED" and len(driver.calls) == 2
    assert engine.prepare_rollback(plan["plan_id"])["approval_required"] is False


def test_expert_fallback_rejects_ftd_and_unregistered_protocol_before_any_driver_call():
    engine = P10ExecutionEngine(BASE)
    evidence = {
        "evidence_id": "ev-critical-fixture", "observed_at": engine._iso(engine._now()),
        "binding_id": "p7-ftd", "target": "ftd.example.invalid", "identity_pin": "SHA256:fixture",
        "state_digest": _digest("critical"), "checks": [{"check_id": "critical_scope_verified", "passed": True, "read_only": True, "evidence_id": "ev-critical-fixture", "observed_at": engine._iso(engine._now())}], "facts": {},
    }
    warning = {key: "fixture" for key in (
        "outside_catalog_reason", "expected_outcome", "blast_radius", "downtime_risk", "management_access_risk",
        "security_risk", "data_loss_risk", "dependencies_affected", "reversibility", "out_of_band_recovery",
    )}
    with pytest.raises(P10SafetyError, match="FMC-managed FTD"):
        engine.prepare_critical_exception(
            platform="cisco_ftd", protocol="ssh_cli", binding_id="p7-ftd", target="ftd.example.invalid",
            identity_pin="SHA256:fixture", commands=["show version"], rollback_commands=["show version"],
            evidence=evidence, warning=warning,
        )
