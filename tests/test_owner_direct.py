"""Offline contract tests for the Owner Direct control plane."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.infrastructure.owner_direct import OwnerDirectError, OwnerDirectService
from core.tools.broker import ToolBroker


BASE = Path(__file__).resolve().parent.parent
ENTITY = "fw-fortigate-hq-01"
SESSION = "a" * 64


class FakeAdapter:
    def __init__(self, *, identity: str = "SHA256:observed", postcheck: str = "SUCCESS"):
        self.identity, self.postcheck = identity, postcheck
        self.read_calls: list[dict] = []
        self.write_calls: list[dict] = []

    def read(self, request: dict) -> dict:
        self.read_calls.append(request)
        if request.get("postcheck"):
            return {"status": self.postcheck, "identity": self.identity}
        return {"status": "SUCCESS", "reachable": True, "authentication": "SUCCESS", "identity": self.identity,
                "facts": {"serial": "FG-TEST", "model": "FGT", "version": "7.4", "password": "never-return-this"}}

    def write(self, request: dict) -> dict:
        self.write_calls.append(request)
        return {"status": "COMMITTED", "submitted": True, "token": "never-return-this"}


def _service(adapter: FakeAdapter | None = None) -> OwnerDirectService:
    service = OwnerDirectService(BASE, adapters={"ssh": adapter or FakeAdapter()})
    # Bindings are not needed for these offline contract tests.  This also
    # proves the service does not read an .env value merely to create a plan.
    service.bindings = []
    return service


def _write(service: OwnerDirectService, **kwargs) -> dict:
    values = {
        "entity_id": ENTITY, "protocol": "ssh", "operations": ["configure firewall address O_DIRECT_TEST"],
        "intended_change": "Create one address object O_DIRECT_TEST.", "expected_impact": "One firewall object changes.",
        "downtime_risk": "No expected service interruption.", "blast_radius": "One exact firewall object.",
        "prechecks": ["Confirm the object does not already exist."], "postchecks": ["Read the object back."],
        "owner_requested": True,
    }
    values.update(kwargs)
    return service.prepare_write(**values)


def test_unpinned_read_collects_identity_once_without_retry_or_pin_update():
    adapter = FakeAdapter(); service = _service(adapter)
    result = service.discover(entity_id=ENTITY, protocol="ssh", operation="get system status")
    assert result["status"] == "SUCCESS"
    assert result["identity_result"] == "IDENTITY_UNVERIFIED"
    assert result["attempt_count"] == 1 and result["automatic_retry"] is False and len(adapter.read_calls) == 1
    assert result["evidence_id"].startswith("ev-owner-direct-") and result["canonical_documents_updated"] is False


def test_identity_conflict_is_explicit_and_never_overwrites_trusted_value():
    service = _service(FakeAdapter(identity="SHA256:new"))
    result = service.discover(entity_id=ENTITY, protocol="ssh", operation="get system status", trusted_identity="SHA256:old")
    assert result["status"] == "IDENTITY_CONFLICT"
    assert result["identity_result"] == "IDENTITY_CONFLICT"
    with pytest.raises(OwnerDirectError, match="IDENTITY_CONFLICT"):
        _write(service, trusted_identity="SHA256:old", observed_identity="SHA256:new")


def test_secret_containment_and_canonical_target_enforcement():
    service = _service()
    result = service.discover(entity_id=ENTITY, protocol="ssh", operation="get system status")
    serialized = json.dumps(result)
    assert "never-return-this" not in serialized and "password" not in serialized.casefold()
    with pytest.raises(OwnerDirectError, match="outside the canonical"):
        service.discover(entity_id="not-an-asset", protocol="ssh", operation="show version")
    with pytest.raises(OwnerDirectError, match="owner-supplied target confirmation"):
        service.discover(entity_id=ENTITY, protocol="ssh", operation="show version", target="198.51.100.9")
    owner_target = service.discover(entity_id=ENTITY, protocol="ssh", operation="show version", target="198.51.100.9", owner_supplied_target=True)
    assert owner_target["new_target_owner_supplied"] is True


def test_write_warning_is_complete_and_final_confirmation_is_the_only_execution_gate():
    adapter = FakeAdapter(); service = _service(adapter)
    plan = _write(service, rollback_steps=[])
    warning = plan["warning"]
    assert plan["status"] == "AWAITING_FINAL_CONFIRMATION"
    assert "credential_reference" not in json.dumps(plan)
    assert warning["rollback_status"] == "NO_SAFE_ROLLBACK"
    assert all(key in warning for key in ("target_device_system", "exact_intended_change", "commands_or_api_operations", "expected_impact_and_downtime_risk", "blast_radius", "prechecks", "postchecks", "rollback_steps", "identity_status"))
    assert adapter.write_calls == []
    result = service.confirm_write(plan["plan_id"], owner_session_digest=SESSION)
    assert result["status"] == "COMMITTED" and result["postcheck_status"] == "SUCCESS"
    assert len(adapter.write_calls) == 1 and len(adapter.read_calls) == 1
    with pytest.raises(OwnerDirectError, match="already confirmed"):
        service.confirm_write(plan["plan_id"], owner_session_digest=SESSION)


def test_malformed_write_is_rejected_before_adapter_and_audit_proposes_only():
    adapter = FakeAdapter(); service = _service(adapter)
    with pytest.raises(OwnerDirectError, match="injection"):
        _write(service, operations=["configure x; reboot"])
    audit = service.identity_audit(requests=[{"entity_id": ENTITY, "protocol": "ssh", "operation": "get system status"}])
    assert audit["audit_status"] == "COMPLETE" and audit["attempts"] == 1
    assert audit["pins_updated"] is False and audit["canonical_documents_updated"] is False
    assert audit["proposed_correction_enrollment_batch"]


def test_tool_broker_exposes_owner_direct_to_both_agent_surfaces_without_final_write_tool():
    adapter = FakeAdapter()
    broker = ToolBroker(BASE, owner_direct_adapters={"ssh": adapter})
    broker.owner_direct.bindings = []
    names = {item["name"] for item in broker.registry.provider_tools(broker.permissions.modes["OWNER_DIRECT"])}
    assert {"owner_direct.discover", "owner_direct.prepare_write", "owner_direct.identity_audit"}.issubset(names)
    assert "owner_direct.confirm_write" not in names
    call = broker.propose(
        thread_id="thr_" + "a" * 20, turn_id="trn_" + "b" * 20, tool_name="owner_direct.discover",
        arguments={"entity_id": ENTITY, "protocol": "ssh", "operation": "get system status"}, permission_mode="OWNER_DIRECT",
    )
    result = broker.invoke(call["tool_call_id"], owner_session_digest=SESSION)["result"]
    assert result["identity_result"] == "IDENTITY_UNVERIFIED" and result["credentials_returned"] is False
