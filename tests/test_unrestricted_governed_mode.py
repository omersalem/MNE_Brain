"""Unit and contract tests for Unrestricted Read & Transparent Risk/Rollback Write Mode."""

import os
from pathlib import Path
import pytest

from core.infrastructure.owner_direct import OwnerDirectError, OwnerDirectService
from core.policy.policy_engine import PolicyEngine

BASE = Path(__file__).resolve().parent.parent
ENTITY = "fw-fortigate-jenin-01"
SESSION = "f" * 64


class MockAdapter:
    def __init__(self, identity: str = "SHA256:test_identity"):
        self.identity = identity
        self.read_calls = []
        self.write_calls = []

    def read(self, request: dict) -> dict:
        self.read_calls.append(request)
        return {
            "status": "SUCCESS",
            "reachable": True,
            "authentication": "SUCCESS",
            "identity": self.identity,
            "facts": {"serial": "FG-JENIN-01", "model": "FortiGate-60F", "version": "v7.0.12"},
        }

    def write(self, request: dict) -> dict:
        self.write_calls.append(request)
        return {"status": "COMMITTED", "submitted": True}


def _get_service(adapter: MockAdapter | None = None) -> OwnerDirectService:
    service = OwnerDirectService(BASE, adapters={"ssh": adapter or MockAdapter(), "powershell": adapter or MockAdapter()})
    service.bindings = []
    return service


def test_unrestricted_read_diagnostics_accepted():
    """Verify that network diagnostic commands pass read validation and execute."""
    adapter = MockAdapter()
    service = _get_service(adapter)

    diagnostic_commands = [
        "diagnose vpn tunnel list",
        "diagnose sys session filter dport 443",
        "execute ping 10.201.18.1",
        "execute traceroute 172.23.13.201",
        "ping 8.8.8.8",
        "traceroute 1.1.1.1",
        "show full-configuration",
        "get router info routing-table all",
        "cat /proc/uptime",
        "uptime",
    ]

    for cmd in diagnostic_commands:
        result = service.discover(entity_id=ENTITY, protocol="ssh", operation=cmd)
        assert result["status"] == "SUCCESS", f"Failed for command: {cmd}"
        assert result["reachability"] is True

    # Test PowerShell networking commands
    ps_commands = [
        "Test-NetConnection -ComputerName 172.23.71.27 -Port 53",
        "Resolve-DnsName -Name dc-mne-ad-01",
        "Get-NetIPAddress",
        "Get-Service -Name W32Time",
    ]
    for ps_cmd in ps_commands:
        result = service.discover(entity_id="dc-mne-ad-01", protocol="powershell", operation=ps_cmd)
        assert result["status"] == "SUCCESS", f"Failed for PS command: {ps_cmd}"


def test_write_risk_classification():
    """Verify automatic risk classification for various operational commands."""
    service = _get_service()

    # CRITICAL
    plan_crit = service.prepare_write(
        entity_id=ENTITY,
        protocol="ssh",
        operations=["execute reboot"],
        intended_change="Reboot firewall",
        expected_impact="Downtime",
        downtime_risk="2m",
        blast_radius="Branch",
        prechecks=["ping gw"],
        postchecks=["ping gw"],
        owner_requested=True,
    )
    assert plan_crit["risk_level"] == "CRITICAL"
    assert plan_crit["warning"]["risk_level"] == "CRITICAL"

    # HIGH
    plan_high = service.prepare_write(
        entity_id=ENTITY,
        protocol="ssh",
        operations=["config router static", "edit 1", "set distance 10", "end"],
        intended_change="Update default route",
        expected_impact="Routing failover",
        downtime_risk="None",
        blast_radius="WAN",
        prechecks=["show route"],
        postchecks=["show route"],
        owner_requested=True,
    )
    assert plan_high["risk_level"] == "HIGH"
    assert plan_high["warning"]["risk_level"] == "HIGH"

    # MEDIUM
    plan_med = service.prepare_write(
        entity_id=ENTITY,
        protocol="ssh",
        operations=["config system interface", "edit port1", "set description WAN_UPLINK", "end"],
        intended_change="Set interface description",
        expected_impact="None",
        downtime_risk="None",
        blast_radius="Port1",
        prechecks=["show interface"],
        postchecks=["show interface"],
        owner_requested=True,
    )
    assert plan_med["risk_level"] == "MEDIUM"

    # LOW
    plan_low = service.prepare_write(
        entity_id=ENTITY,
        protocol="ssh",
        operations=["config system global", "set timezone 04", "end"],
        intended_change="Set timezone",
        expected_impact="None",
        downtime_risk="None",
        blast_radius="None",
        prechecks=["get system status"],
        postchecks=["get system status"],
        owner_requested=True,
    )
    assert plan_low["risk_level"] == "LOW"


def test_write_rollback_transparency():
    """Verify explicit rollback transparency when rollback steps are provided vs empty."""
    service = _get_service()

    # Reversible plan with declared rollback
    reversible_plan = service.prepare_write(
        entity_id=ENTITY,
        protocol="ssh",
        operations=["config router static", "edit 1", "set distance 10", "end"],
        intended_change="Adjust distance",
        expected_impact="None",
        downtime_risk="None",
        blast_radius="Local",
        prechecks=["check"],
        postchecks=["check"],
        rollback_steps=["config router static", "edit 1", "set distance 1", "end"],
        owner_requested=True,
    )
    assert reversible_plan["can_rollback"] is True
    assert reversible_plan["warning"]["can_rollback"] is True
    assert reversible_plan["warning"]["rollback_status"] == "DECLARED"
    assert "Automated rollback available (4 step(s) declared)" in reversible_plan["rollback_summary"]

    # Irreversible plan with NO rollback
    irreversible_plan = service.prepare_write(
        entity_id=ENTITY,
        protocol="ssh",
        operations=["execute formatlogdisk"],
        intended_change="Format log disk",
        expected_impact="Log data loss",
        downtime_risk="None",
        blast_radius="Disk",
        prechecks=["check"],
        postchecks=["check"],
        rollback_steps=[],
        owner_requested=True,
    )
    assert irreversible_plan["can_rollback"] is False
    assert irreversible_plan["warning"]["can_rollback"] is False
    assert irreversible_plan["warning"]["rollback_status"] == "NO_SAFE_ROLLBACK"
    assert "IRREVERSIBLE / NO SAFE ROLLBACK" in irreversible_plan["rollback_summary"]


def test_write_execution_requires_admin_confirmation():
    """Verify write execution remains gated until admin explicitly confirms."""
    adapter = MockAdapter()
    service = _get_service(adapter)

    plan = service.prepare_write(
        entity_id=ENTITY,
        protocol="ssh",
        operations=["config system dns", "set primary 172.23.71.27", "end"],
        intended_change="Update primary DNS",
        expected_impact="DNS lookup update",
        downtime_risk="None",
        blast_radius="DNS resolution",
        prechecks=["check"],
        postchecks=["check"],
        rollback_steps=["config system dns", "set primary 172.23.71.28", "end"],
        owner_requested=True,
    )
    assert plan["status"] == "AWAITING_FINAL_CONFIRMATION"
    assert adapter.write_calls == []  # Not called yet

    # Admin confirms execution
    result = service.confirm_write(plan["plan_id"], owner_session_digest=SESSION)
    assert result["status"] == "COMMITTED"
    assert len(adapter.write_calls) == 1
    assert result["can_rollback"] is True


def test_policy_engine_unrestricted_read_env_toggle(monkeypatch):
    """Verify MNE_UNRESTRICTED_READ enables live verification without manual gate."""
    # Default without env var
    default_engine = PolicyEngine(base_dir=BASE)
    assert default_engine.policy_data.get("live_verification", {}).get("enabled") is False

    # With MNE_UNRESTRICTED_READ=true
    monkeypatch.setenv("MNE_UNRESTRICTED_READ", "true")
    unrestricted_engine = PolicyEngine(base_dir=BASE)
    assert unrestricted_engine.policy_data.get("live_verification", {}).get("enabled") is True
    assert unrestricted_engine.policy_data.get("live_verification", {}).get("requires_explicit_authorization") is False
