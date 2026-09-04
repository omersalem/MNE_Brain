"""Mocked live-driver, renderer, readiness, and failure tests for all P10 platforms."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.execution.p10_catalog import P10CatalogError, P10OperationCatalog
from core.execution.p10_commands import render_wire
from core.execution.p10_readiness import P10ReadinessService
from core.execution.p10_engine import OWNER_REFERENCE, P10ExecutionEngine
from core.tools.drivers.p10_live import P10LiveDriverError, P10LivePlatformDriver


BASE = Path(__file__).resolve().parent.parent


CASES = [
    ("fortinet_fortios", "p10-fortigate-address-object", "create_address", {"resource_name": "SAFE", "value": "192.0.2.10"}, "config firewall address", "ssh_cli"),
    ("f5_bigip", "p10-f5-node", "create_node", {"resource_name": "SAFE", "value": "192.0.2.10"}, "tmsh create ltm node", "ssh_cli"),
    ("cisco_fmc", "p10-fmc-network-object", "create_host", {"resource_name": "SAFE", "value": "192.0.2.10"}, "POST /api/fmc_config", "https_json"),
    ("windows_powershell", "p10-windows-service", "start_service", {"resource_name": "Spooler"}, "Start-Service", "winrm_powershell"),
    ("vmware_vcenter", "p10-vmware-power", "power_on", {"resource_name": "vm-101"}, "POST /api/vcenter/vm/vm-101/power", "https_json"),
    ("cisco_switching", "p10-cisco-vlan", "create_vlan", {"resource_name": "210"}, "configure terminal", "ssh_cli"),
    ("fujitsu_switching", "p10-fujitsu-vlan", "create_vlan", {"resource_name": "210"}, "configure terminal", "ssh_cli"),
    ("linux_host", "p10-linux-service", "start_service", {"resource_name": "nginx"}, "sudo -n systemctl start nginx", "ssh_cli"),
]


def _transaction(catalog, operation_id, action, arguments, *, target="example.invalid", rollback=False):
    operation = catalog.get(operation_id)
    return {
        "transaction_version": "1.0", "platform": operation["platform"], "operation_id": operation_id,
        "operation_type": operation["operation_type"], "renderer": operation["rollback_renderer"] if rollback else operation["command_renderer"],
        "target": target, "action": action, "arguments": {key: value for key, value in arguments.items() if key != "action"},
        "transaction_mode": operation["transaction_mode"], "rollback": rollback,
    }


@pytest.mark.parametrize("platform,operation_id,action,arguments,expected,protocol", CASES)
def test_every_platform_renders_exact_vendor_command(platform, operation_id, action, arguments, expected, protocol):
    transaction = _transaction(P10OperationCatalog(BASE), operation_id, action, arguments)
    wire = render_wire(transaction)
    assert transaction["platform"] == platform
    assert wire["protocol"] == protocol
    assert expected in "\n".join(wire["display"])


@pytest.mark.parametrize("platform,operation_id,action,arguments,_expected,protocol", CASES)
def test_every_live_driver_routes_only_the_approved_wire(monkeypatch, platform, operation_id, action, arguments, _expected, protocol):
    transaction = _transaction(P10OperationCatalog(BASE), operation_id, action, arguments)
    wire = render_wire(transaction)
    item = {"sequence": 1, "display": wire["display"][0], "transaction": transaction, "wire": wire}
    driver = P10LivePlatformDriver(BASE, platform=platform)
    driver._authorized.add(("p7-test", "example.invalid"))
    monkeypatch.setattr(driver, "_binding", lambda binding_id, target: ({"binding_id": binding_id}, "MNE_TEST"))
    monkeypatch.setattr(driver, "_write_credentials", lambda prefix: ("secretref://test/write", "fixture-user", "fixture-password"))
    invoked = []
    method = "_winrm" if protocol == "winrm_powershell" else ("_https" if protocol == "https_json" else "_ssh")
    monkeypatch.setattr(driver, method, lambda *args, **kwargs: invoked.append((args, kwargs)) or {"status": "COMMITTED", "submitted": True, "output": None})
    result = driver.execute(binding_id="p7-test", target="example.invalid", commands=[item], timeout_seconds=15)
    assert result["status"] == "COMMITTED" and len(invoked) == 1


def test_readiness_lists_every_platform_and_never_claims_write_authorization():
    result = P10ReadinessService(BASE).status()
    assert result["status"] == "BLOCKED_BEFORE_FIRST_REAL_WRITE"
    assert {item["platform"] for item in result["platforms"]} == {item[0] for item in CASES}
    assert all(item["global_write_enabled"] is False and item["live_write_ready"] is False for item in result["platforms"])
    assert all(binding["write_authorization"] in {"NOT_CONFIGURED", "NOT_CHECKED"} for item in result["platforms"] for binding in item["bindings"])


@pytest.mark.parametrize("platform,probe_output", [
    ("fortinet_fortios", 'set accprofile "super_admin"'),
    ("f5_bigip", "role administrator"),
    ("cisco_fmc", '{"role":"Admin"}'),
    ("windows_powershell", "BUILTIN\\Administrators S-1-5-32-544 Enabled"),
    ("cisco_switching", "Current privilege level is 15"),
    ("fujitsu_switching", "Privilege level 15"),
    ("linux_host", "(ALL : ALL) ALL"),
])
def test_read_only_privilege_probes_establish_only_explicit_write_roles(monkeypatch, platform, probe_output):
    driver = P10LivePlatformDriver(BASE, platform=platform)
    monkeypatch.setattr(driver, "_binding", lambda binding_id, target: ({"binding_id": binding_id}, "MNE_TEST"))
    monkeypatch.setattr(driver, "_write_credentials", lambda prefix: ("secretref://test/write", "fixture-user", "fixture-password"))
    result = {"status": "SUCCESS", "connection_attempted": True, "output": probe_output}
    if platform == "cisco_fmc": monkeypatch.setattr(driver, "_https_read", lambda *a, **k: result.copy())
    elif platform == "windows_powershell": monkeypatch.setattr(driver, "_winrm_read_with_credentials", lambda *a, **k: result.copy())
    else: monkeypatch.setattr(driver, "_ssh_read", lambda *a, **k: result.copy())
    checked = driver.probe_write_authorization(binding_id="p7-test", target="example.invalid")
    assert checked["status"] == "WRITE_AUTHORIZED" and checked["write_authorized"] is True
    assert ("p7-test", "example.invalid") in driver._authorized


def test_vcenter_write_authorization_probe_fails_closed_without_decisive_privilege_api(monkeypatch):
    driver = P10LivePlatformDriver(BASE, platform="vmware_vcenter")
    monkeypatch.setattr(driver, "_binding", lambda binding_id, target: ({"binding_id": binding_id}, "MNE_TEST"))
    monkeypatch.setattr(driver, "_write_credentials", lambda prefix: ("secretref://test/write", "fixture-user", "fixture-password"))
    result = driver.probe_write_authorization(binding_id="p7-test", target="example.invalid")
    assert result["status"] == "AUTHORIZATION_PROBE_UNAVAILABLE" and result["write_authorized"] is False


@pytest.mark.parametrize("platform,operation_id,action,arguments,_expected,_protocol", CASES)
def test_every_live_driver_blocks_missing_separate_write_credential_without_connection(monkeypatch, platform, operation_id, action, arguments, _expected, _protocol):
    driver = P10LivePlatformDriver(BASE, platform=platform)
    monkeypatch.setattr(driver, "_binding", lambda binding_id, target: ({"binding_id": binding_id}, "MNE_TEST"))
    monkeypatch.setattr(driver.credentials, "value", lambda key: "")
    transaction = _transaction(P10OperationCatalog(BASE), operation_id, action, arguments)
    wire = render_wire(transaction)
    with pytest.raises(P10LiveDriverError, match="Separate write authorization"):
        driver.execute(binding_id="p7-test", target="example.invalid", commands=[{"sequence": 1, "display": wire["display"][0], "transaction": transaction, "wire": wire}], timeout_seconds=15)


def test_display_wire_tampering_and_underspecified_actions_fail_closed(monkeypatch):
    driver = P10LivePlatformDriver(BASE, platform="linux_host")
    driver._authorized.add(("p7-test", "example.invalid"))
    monkeypatch.setattr(driver, "_binding", lambda binding_id, target: ({"binding_id": binding_id}, "MNE_TEST"))
    monkeypatch.setattr(driver, "_write_credentials", lambda prefix: ("secretref://test/write", "fixture-user", "fixture-password"))
    transaction = _transaction(P10OperationCatalog(BASE), "p10-linux-service", "start_service", {"resource_name": "nginx"})
    wire = render_wire(transaction)
    tampered = {"sequence": 1, "display": "sudo -n reboot", "transaction": transaction, "wire": wire}
    with pytest.raises(P10LiveDriverError, match="differ"):
        driver.execute(binding_id="p7-test", target="example.invalid", commands=[tampered], timeout_seconds=15)
    catalog = P10OperationCatalog(BASE)
    operation = catalog.get("p10-fmc-access-rule")
    with pytest.raises(P10CatalogError, match="exact object"):
        catalog.render(operation, {"action": "create_disabled_rule", "resource_name": "SAFE"}, target="fmc.example.invalid")


def test_engine_live_path_runs_authorization_fresh_state_single_submit_and_independent_postcheck():
    class LiveHarness:
        live = True
        simulation = False
        submissions = 0
        def probe_write_authorization(self, **_kwargs): return {"status": "WRITE_AUTHORIZED", "write_authorized": True}
        def capture_state(self, *, postcheck=False, **_kwargs):
            return {"status": "SUCCESS", "identity_pin": "SHA256:offline-pinned-identity", "state_digest": "1" * 64,
                    "effect_verified": bool(postcheck), "connection_attempted": False}
        def execute(self, **_kwargs): self.submissions += 1; return {"status": "COMMITTED", "submitted": True, "output": None}
        def abort(self, **_kwargs): return {"status": "ABORT_UNAVAILABLE"}
    harness = LiveHarness(); engine = P10ExecutionEngine(BASE, execution_enabled=True, driver=harness)
    operation = engine.catalog.get("p10-fortigate-address-object")
    now = engine._iso(engine._now())
    evidence = {"evidence_id": "ev-live-harness", "observed_at": now, "binding_id": "p7-fortigate-edge", "target": "fw.example.invalid",
                "identity_pin": "SHA256:offline-pinned-identity", "state_digest": "0" * 64,
                "checks": [{"check_id": check, "passed": True, "read_only": True, "evidence_id": "ev-live-harness", "observed_at": now} for check in operation["pre_checks"]], "facts": {}}
    session = "a" * 64
    plan = engine.prepare("p10-fortigate-address-object", binding_id="p7-fortigate-edge", target="fw.example.invalid",
                          identity_pin="SHA256:offline-pinned-identity", parameters={"action": "create_address", "resource_name": "SAFE", "value": "192.0.2.10"}, evidence=evidence, owner_session_digest=session)
    engine.approve(plan["plan_id"], engine.expected_approval_phrase(plan["plan_id"]), owner_reference=OWNER_REFERENCE, owner_session_digest=session)
    result = engine.execute(plan["plan_id"], owner_session_digest=session)
    assert result["status"] == "SUCCESS" and harness.submissions == 1
