"""Comprehensive offline safety tests for P10 owner-controlled writes."""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema
import pytest
import yaml

from core.api.p10_local import P10LocalAPIContext
from core.execution.p10_catalog import P10CatalogError, P10OperationCatalog
from core.execution.p10_engine import OWNER_REFERENCE, P10ExecutionEngine, P10SafetyError
from core.tools.drivers.p10_write import PLATFORM_DRIVER_FAMILIES, P10PlatformDriverRegistry, SimulatedP10WriteDriver


BASE = Path(__file__).resolve().parent.parent


class Clock:
    def __init__(self):
        self.value = datetime(2026, 8, 20, 9, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.value


def _digest(label: str = "stable") -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _operation(engine: P10ExecutionEngine, operation_id: str):
    return engine.catalog.get(operation_id)


def _evidence(engine: P10ExecutionEngine, operation_id: str, *, binding: str, target: str, pin: str, facts=None, passed=True):
    operation = _operation(engine, operation_id)
    return {
        "evidence_id": "ev-p10-offline-001",
        "observed_at": engine._iso(engine._now()),
        "binding_id": binding,
        "target": target,
        "identity_pin": pin,
        "state_digest": _digest(),
        "checks": [{"check_id": check, "passed": passed, "read_only": True, "evidence_id": "ev-p10-offline-001", "observed_at": engine._iso(engine._now())} for check in operation["pre_checks"]],
        "facts": facts or {},
    }


def _prepare(
    engine: P10ExecutionEngine,
    operation_id: str = "p10-fortigate-address-object",
    *,
    binding: str = "p7-fortigate-edge",
    target: str = "fw.example.invalid",
    pin: str = "SHA256:offline-pinned-identity",
    facts=None,
):
    operation = _operation(engine, operation_id)
    return engine.prepare(
        operation_id,
        binding_id=binding,
        target=target,
        identity_pin=pin,
        parameters={"action": operation["action_variants"][0], "resource_name": "P10_TEST_OBJECT", "value": "192.0.2.10"},
        evidence=_evidence(engine, operation_id, binding=binding, target=target, pin=pin, facts=facts),
    )


def _approve(engine: P10ExecutionEngine, plan: dict):
    return engine.approve(plan["plan_id"], engine.expected_approval_phrase(plan["plan_id"]), owner_reference=OWNER_REFERENCE)


def _probe(plan: dict, *, changed_pin=False, changed_state=False, pending=False):
    internal = plan
    return {
        "identity_pin": "changed" if changed_pin else "SHA256:offline-pinned-identity",
        "state_digest": _digest("changed") if changed_state else _digest(),
        "unrelated_pending_changes": pending,
    }


def _post(_plan, _driver):
    return [{"check_id": "independent_post_check", "passed": True, "read_only": True, "evidence_id": "ev-p10-post-001", "observed_at": datetime.now(timezone.utc).isoformat()}]


def _warning():
    return {
        "outside_catalog_reason": "One-time vendor recovery operation is not cataloged.",
        "expected_outcome": "Recover the exact named object.",
        "blast_radius": "Exact target; service impact is possible.",
        "downtime_risk": "HIGH",
        "management_access_risk": "POSSIBLE",
        "security_risk": "HIGH",
        "data_loss_risk": "POSSIBLE",
        "dependencies_affected": "Named service and direct clients.",
        "reversibility": "Separate rollback approval where available.",
        "out_of_band_recovery": "Must be confirmed before live execution.",
    }


def _critical_evidence(engine, binding="p7-fortigate-edge", target="fw.example.invalid", pin="SHA256:offline-pinned-identity"):
    return {
        "evidence_id": "ev-critical-offline",
        "observed_at": engine._iso(engine._now()),
        "binding_id": binding,
        "target": target,
        "identity_pin": pin,
        "state_digest": _digest(),
        "checks": [{"check_id": "critical_scope_verified", "passed": True, "read_only": True, "evidence_id": "ev-critical-offline", "observed_at": engine._iso(engine._now())}],
        "facts": {},
    }


def test_p10_catalog_schema_policy_and_driver_coverage():
    catalog = P10OperationCatalog(BASE)
    metadata = catalog.list_metadata()
    assert metadata["family_count"] == 7
    assert metadata["template_count"] == 56
    assert metadata["action_variant_count"] == 176
    assert len(PLATFORM_DRIVER_FAMILIES) == 8
    registry = P10PlatformDriverRegistry()
    assert len(registry.adapters) == 8 and registry.live is False
    assert metadata["live_execution_enabled"] is False
    policy = yaml.safe_load((BASE / "config/p10_action_policy.yaml").read_text())
    assert policy["level_4_policy"] == "CRITICAL_EXCEPTION_ONLY"
    assert all(policy[key] is False for key in ("ticketing_enabled", "paging_enabled", "notifications_enabled", "automatic_assignment_enabled", "automatic_remediation_enabled"))


def test_unknown_catalog_and_parameter_fields_are_rejected():
    engine = P10ExecutionEngine(BASE)
    with pytest.raises(P10CatalogError):
        engine.catalog.get("p10-not-listed")
    operation = engine.catalog.get("p10-fortigate-address-object")
    with pytest.raises(P10CatalogError):
        engine.catalog.validate_parameters(operation, {"action": "create_address", "resource_name": "safe", "unknown": "x"})


@pytest.mark.parametrize("value", ["name; reboot", "name && whoami", "$(id)", "name\nnext", "*", "Invoke-Expression x"])
def test_parameter_and_shell_injection_are_rejected(value):
    engine = P10ExecutionEngine(BASE)
    operation = engine.catalog.get("p10-windows-service")
    with pytest.raises(P10CatalogError):
        engine.catalog.validate_parameters(operation, {"action": "start_service", "resource_name": value})


def test_no_approval_means_no_driver_invocation():
    driver = SimulatedP10WriteDriver()
    engine = P10ExecutionEngine(BASE, execution_enabled=True, driver=driver)
    plan = _prepare(engine)
    with pytest.raises(P10SafetyError):
        engine.execute(plan["plan_id"], state_probe=_probe, postcheck_runner=_post)
    assert driver.calls == []


def test_prepared_plan_contains_complete_immutable_change_package():
    plan = _prepare(P10ExecutionEngine(BASE))
    assert plan["intended_changes"] and plan["affected_systems"] == [plan["target"]]
    assert isinstance(plan["dependencies"], list) and plan["pre_check_results"] and plan["post_checks"]
    assert plan["backup_snapshot"] and plan["rollback_conditions"]
    assert isinstance(plan["non_rollbackable_operations"], list)
    assert plan["command_hash"] and plan["rollback_hash"] and plan["target_identity_hash"] and plan["state_digest"]


def test_wrong_owner_plan_hash_and_case_fail_closed():
    engine = P10ExecutionEngine(BASE)
    plan = _prepare(engine)
    exact = engine.expected_approval_phrase(plan["plan_id"])
    for phrase, owner in ((exact, "NOT-OWNER"), (exact.replace(plan["command_hash"], "0" * 64), OWNER_REFERENCE), (exact.lower(), OWNER_REFERENCE)):
        with pytest.raises(P10SafetyError):
            engine.approve(plan["plan_id"], phrase, owner_reference=owner)


def test_wrong_plan_id_and_remote_source_are_rejected():
    engine = P10ExecutionEngine(BASE)
    plan = _prepare(engine)
    with pytest.raises(P10SafetyError):
        engine.approve("p10-00000000000000000000", "x", owner_reference=OWNER_REFERENCE)
    with pytest.raises(P10SafetyError):
        engine.approve(plan["plan_id"], engine.expected_approval_phrase(plan["plan_id"]), owner_reference=OWNER_REFERENCE, source="remote")


def test_expired_approval_and_replay_are_rejected():
    clock = Clock()
    engine = P10ExecutionEngine(BASE, now=clock)
    expired = _prepare(engine)
    clock.value += timedelta(seconds=301)
    with pytest.raises(P10SafetyError):
        _approve(engine, expired)
    clock = Clock()
    engine = P10ExecutionEngine(BASE, now=clock)
    plan = _prepare(engine)
    _approve(engine, plan)
    with pytest.raises(P10SafetyError):
        _approve(engine, plan)


@pytest.mark.parametrize("field", ["target", "command_hash", "rollback_hash", "target_identity_hash", "risk_level"])
def test_modified_prepared_content_invalidates_approval(field):
    engine = P10ExecutionEngine(BASE)
    plan = _prepare(engine)
    engine._plans[plan["plan_id"]][field] = "changed" if field != "risk_level" else 4
    with pytest.raises(P10SafetyError):
        _approve(engine, plan)


def test_stale_evidence_failed_precheck_and_changed_identity_are_blocked():
    clock = Clock()
    engine = P10ExecutionEngine(BASE, now=clock)
    evidence = _evidence(engine, "p10-fortigate-address-object", binding="p7-fortigate-edge", target="fw.example.invalid", pin="SHA256:offline-pinned-identity")
    evidence["observed_at"] = engine._iso(clock.value - timedelta(seconds=301))
    with pytest.raises(P10SafetyError, match="stale"):
        engine.prepare("p10-fortigate-address-object", binding_id="p7-fortigate-edge", target="fw.example.invalid", identity_pin="SHA256:offline-pinned-identity", parameters={"action": "create_address", "resource_name": "SAFE", "value": "192.0.2.10"}, evidence=evidence)
    evidence = _evidence(engine, "p10-fortigate-address-object", binding="p7-fortigate-edge", target="fw.example.invalid", pin="SHA256:offline-pinned-identity", passed=False)
    with pytest.raises(P10SafetyError, match="pre-checks"):
        engine.prepare("p10-fortigate-address-object", binding_id="p7-fortigate-edge", target="fw.example.invalid", identity_pin="SHA256:offline-pinned-identity", parameters={"action": "create_address", "resource_name": "SAFE", "value": "192.0.2.10"}, evidence=evidence)
    driver = SimulatedP10WriteDriver()
    enabled = P10ExecutionEngine(BASE, execution_enabled=True, driver=driver)
    plan = _prepare(enabled)
    _approve(enabled, plan)
    result = enabled.execute(plan["plan_id"], state_probe=lambda p: _probe(p, changed_pin=True), postcheck_runner=_post)
    assert result["status"] == "IDENTITY_PIN_CHANGED" and driver.calls == []


def test_precheck_state_pending_changes_and_cancellation_stop_before_submission():
    for expected, probe in (("PRECHECK_STATE_CHANGED", lambda p: _probe(p, changed_state=True)), ("UNRELATED_PENDING_CHANGES", lambda p: _probe(p, pending=True))):
        driver = SimulatedP10WriteDriver()
        engine = P10ExecutionEngine(BASE, execution_enabled=True, driver=driver)
        plan = _prepare(engine)
        _approve(engine, plan)
        assert engine.execute(plan["plan_id"], state_probe=probe, postcheck_runner=_post)["status"] == expected
        assert driver.calls == []
    driver = SimulatedP10WriteDriver()
    engine = P10ExecutionEngine(BASE, execution_enabled=True, driver=driver)
    plan = _prepare(engine); _approve(engine, plan)
    cancel = threading.Event(); cancel.set()
    assert engine.execute(plan["plan_id"], state_probe=_probe, postcheck_runner=_post, cancellation_event=cancel)["status"] == "CANCELLED"
    assert driver.calls == []


def test_normal_success_requires_independent_postcheck_and_no_retry():
    driver = SimulatedP10WriteDriver([{"status": "SUBMITTED", "submitted": True}])
    engine = P10ExecutionEngine(BASE, execution_enabled=True, driver=driver)
    plan = _prepare(engine); _approve(engine, plan)
    result = engine.execute(plan["plan_id"], state_probe=_probe, postcheck_runner=_post)
    assert result["status"] == "SUCCESS" and len(driver.calls) == 1
    assert result["rollback_status"] == "NOT_TRIGGERED"
    assert result["output_persisted"] is False and result["credentials_included"] is False


def test_failed_postcheck_runs_only_preapproved_rollback_and_uncertain_timeout_never_retries():
    driver = SimulatedP10WriteDriver([
        {"status": "SUBMITTED", "submitted": True},
        {"status": "COMMITTED", "submitted": True},
    ])
    engine = P10ExecutionEngine(BASE, execution_enabled=True, driver=driver)
    plan = _prepare(engine); _approve(engine, plan)
    failed = engine.execute(plan["plan_id"], state_probe=_probe, postcheck_runner=lambda p, d: [{"check_id": "post", "passed": False, "read_only": True, "evidence_id": "ev-post-failed", "observed_at": datetime.now(timezone.utc).isoformat()}])
    assert failed["status"] == "ROLLED_BACK_AFTER_POSTCHECK_FAILURE" and failed["success"] is False
    assert failed["rollback_status"] == "VERIFIED" and failed["rollback_result"]["verified"] is True
    assert len(driver.calls) == 2
    for state in ("TIMEOUT", "UNCERTAIN"):
        driver = SimulatedP10WriteDriver([{"status": state, "submitted": True}])
        engine = P10ExecutionEngine(BASE, execution_enabled=True, driver=driver)
        plan = _prepare(engine); _approve(engine, plan)
        result = engine.execute(plan["plan_id"], state_probe=_probe, postcheck_runner=_post)
        assert result["status"] == "UNCERTAIN" and len(driver.calls) == 1


def test_driver_exception_and_oversized_output_are_sanitized_without_retry():
    class RaisingDriver:
        live = False
        simulation = True
        calls = 0
        def execute(self, **_kwargs):
            self.calls += 1
            raise RuntimeError("sensitive driver exception must not escape")

    raising = RaisingDriver()
    engine = P10ExecutionEngine(BASE, execution_enabled=True, driver=raising)
    plan = _prepare(engine); _approve(engine, plan)
    result = engine.execute(plan["plan_id"], state_probe=_probe, postcheck_runner=_post)
    assert result["status"] == "UNCERTAIN" and raising.calls == 1
    assert "exception" not in json.dumps(result).lower()

    driver = SimulatedP10WriteDriver([{"status": "SUBMITTED", "submitted": True, "output": "x" * 131073}])
    engine = P10ExecutionEngine(BASE, execution_enabled=True, driver=driver)
    plan = _prepare(engine); _approve(engine, plan)
    result = engine.execute(plan["plan_id"], state_probe=_probe, postcheck_runner=_post)
    assert result["status"] == "UNCERTAIN" and len(driver.calls) == 1
    assert "x" * 100 not in json.dumps(result)


def test_postcheck_receives_only_sanitized_submission_metadata():
    driver = SimulatedP10WriteDriver([{"status": "SUBMITTED", "submitted": True, "output": "sensitive raw output"}])
    engine = P10ExecutionEngine(BASE, execution_enabled=True, driver=driver)
    plan = _prepare(engine); _approve(engine, plan)
    observed = {}
    def postcheck(_plan, metadata):
        observed.update(metadata)
        return _post(_plan, metadata)
    result = engine.execute(plan["plan_id"], state_probe=_probe, postcheck_runner=postcheck)
    assert result["status"] == "SUCCESS"
    assert set(observed) <= {"status", "submitted", "transaction_state", "transaction_id"}
    assert "output" not in observed


def test_global_concurrency_gate_blocks_second_execution():
    driver = SimulatedP10WriteDriver()
    engine = P10ExecutionEngine(BASE, execution_enabled=True, driver=driver)
    plan = _prepare(engine); _approve(engine, plan)
    assert P10ExecutionEngine._global_execution_lock.acquire(blocking=False)
    try:
        result = engine.execute(plan["plan_id"], state_probe=_probe, postcheck_runner=_post)
    finally:
        P10ExecutionEngine._global_execution_lock.release()
    assert result["status"] == "CONCURRENT_EXECUTION_BLOCKED" and driver.calls == []


def test_f5_open_transaction_aborts_but_committed_rollback_never_auto_runs():
    driver = SimulatedP10WriteDriver([{"status": "FAILED", "submitted": True, "transaction_state": "OPEN", "transaction_id": "tx-offline-1"}])
    engine = P10ExecutionEngine(BASE, execution_enabled=True, driver=driver)
    plan = _prepare(engine, "p10-f5-node", binding="p7-f5", target="f5.example.invalid")
    _approve(engine, plan)
    result = engine.execute(plan["plan_id"], state_probe=_probe, postcheck_runner=_post)
    assert result["status"] == "FAILED_TRANSACTION_ABORTED"
    assert driver.abort_calls == ["tx-offline-1"] and len(driver.calls) == 1


def test_rollback_contract_is_already_covered_by_the_original_single_approval():
    driver = SimulatedP10WriteDriver()
    engine = P10ExecutionEngine(BASE, execution_enabled=True, driver=driver)
    plan = _prepare(engine); _approve(engine, plan)
    engine.execute(plan["plan_id"], state_probe=_probe, postcheck_runner=_post)
    rollback = engine.prepare_rollback(plan["plan_id"])
    assert rollback == {
        "original_plan_id": plan["plan_id"], "rollback_hash": plan["rollback_hash"],
        "approval_required": False, "post_checks": plan["post_checks"],
        "strategy": "PREAPPROVED_AUTOMATIC_ON_DECLARED_FAILURE",
    }
    assert len(driver.calls) == 1


def test_critical_and_irreversible_exact_phrases_and_no_safe_rollback_warning():
    engine = P10ExecutionEngine(BASE)
    critical = engine.prepare_critical_exception(
        platform="fortinet_fortios", binding_id="p7-fortigate-edge", target="fw.example.invalid",
        identity_pin="SHA256:offline-pinned-identity", commands=["execute reviewed vendor recovery SAFE_OBJECT"],
        rollback_commands=[], evidence=_critical_evidence(engine), warning=_warning(),
    )
    assert critical["approval_kind"] == "CRITICAL"
    assert critical["critical_warning"]["rollback"] == "NO SAFE ROLLBACK"
    assert engine.expected_approval_phrase(critical["plan_id"]).startswith("APPROVE CRITICAL ")
    _approve(engine, critical)
    irreversible = engine.prepare_critical_exception(
        platform="fortinet_fortios", binding_id="p7-fortigate-edge", target="fw.example.invalid",
        identity_pin="SHA256:offline-pinned-identity", commands=["execute reviewed irreversible operation SAFE_OBJECT"],
        rollback_commands=[], evidence=_critical_evidence(engine), warning=_warning(), irreversible=True,
    )
    assert engine.expected_approval_phrase(irreversible["plan_id"]).endswith("I ACCEPT PERMANENT DATA OR SERVICE LOSS")
    _approve(engine, irreversible)


def test_destructive_critical_command_requires_irreversible_mode():
    engine = P10ExecutionEngine(BASE)
    with pytest.raises(P10SafetyError, match="irreversible"):
        engine.prepare_critical_exception(
            platform="fortinet_fortios", binding_id="p7-fortigate-edge", target="fw.example.invalid",
            identity_pin="SHA256:offline-pinned-identity", commands=["execute factory-reset SAFE_OBJECT"],
            rollback_commands=[], evidence=_critical_evidence(engine), warning=_warning(), irreversible=False,
        )


@pytest.mark.parametrize("command", ["show safe; delete all", "show safe && reboot", "curl https://example.invalid/x", "set password=Secret123", "delete *"])
def test_critical_exception_hidden_chains_downloads_wildcards_and_secrets_are_rejected(command):
    engine = P10ExecutionEngine(BASE)
    with pytest.raises(P10SafetyError):
        engine.prepare_critical_exception(
            platform="fortinet_fortios", binding_id="p7-fortigate-edge", target="fw.example.invalid",
            identity_pin="SHA256:offline-pinned-identity", commands=[command], rollback_commands=[],
            evidence=_critical_evidence(engine), warning=_warning(),
        )


@pytest.mark.parametrize("operation_id,binding,target,fact", [
    ("p10-fmc-deployment", "p7-fmc-rest", "fmc.example.invalid", "unrelated_pending_changes"),
    ("p10-fortigate-address-object", "p7-fortigate-edge", "fw.example.invalid", "object_conflict"),
    ("p10-cisco-access-vlan", "p7-cisco-core", "switch.example.invalid", "management_uplink"),
    ("p10-vmware-power", "p7-vcenter-rest", "vcenter.example.invalid", "capacity_insufficient"),
])
def test_platform_specific_prohibited_states_block_preparation(operation_id, binding, target, fact):
    engine = P10ExecutionEngine(BASE)
    with pytest.raises(P10SafetyError):
        _prepare(engine, operation_id, binding=binding, target=target, facts={fact: True})


def test_wildcard_batch_and_binding_mismatch_are_rejected():
    engine = P10ExecutionEngine(BASE)
    with pytest.raises(P10SafetyError):
        _prepare(engine, target="*.example.invalid")
    with pytest.raises(P10SafetyError):
        _prepare(engine, "p10-f5-node", binding="p7-fortigate-edge", target="f5.example.invalid")
    assert _operation(engine, "p10-f5-node")["maximum_targets"] == 1


def test_unreviewed_template_is_rejected():
    engine = P10ExecutionEngine(BASE)
    engine.catalog._operations["p10-fortigate-address-object"]["template_status"] = "draft"
    with pytest.raises(P10CatalogError):
        _prepare(engine)


def test_local_api_csrf_replay_and_remote_owner_boundaries():
    context = P10LocalAPIContext(P10ExecutionEngine(BASE))
    nonce = "offline_nonce_0001"
    context.authorize_mutation(client_host="127.0.0.1", csrf_token=context.csrf_token, nonce=nonce)
    with pytest.raises(P10SafetyError, match="replay"):
        context.authorize_mutation(client_host="127.0.0.1", csrf_token=context.csrf_token, nonce=nonce)
    with pytest.raises(P10SafetyError):
        context.authorize_mutation(client_host="192.0.2.10", csrf_token=context.csrf_token, nonce="offline_nonce_0002")
    with pytest.raises(P10SafetyError):
        context.authorize_mutation(client_host="127.0.0.1", csrf_token="wrong", nonce="offline_nonce_0003")
    with pytest.raises(P10SafetyError, match="same-origin"):
        context.authorize_mutation(client_host="127.0.0.1", csrf_token=context.csrf_token, nonce="offline_nonce_0004", host_header="attacker.invalid", origin_header="https://attacker.invalid")


def test_in_memory_audit_zero_enterprise_side_effects_and_no_live_connections(tmp_path):
    driver = SimulatedP10WriteDriver()
    engine = P10ExecutionEngine(BASE, execution_enabled=True, driver=driver)
    plan = _prepare(engine); _approve(engine, plan)
    result = engine.execute(plan["plan_id"], state_probe=_probe, postcheck_runner=_post)
    assert engine.audit_records and all(record["persisted"] is False for record in engine.audit_records)
    assert not list(tmp_path.rglob("*"))
    assert driver.live is False and all(call.get("connection_attempted") is None for call in driver.calls)
    assert all(result[key] is False for key in ("notification_sent", "ticket_created", "page_sent", "automatic_assignment", "automatic_remediation"))
    serialized = json.dumps({"plan": plan, "result": result, "audit": engine.audit_records})
    assert "SHA256:offline-pinned-identity" not in serialized
    assert "password" not in serialized.lower()


def test_p10_schemas_are_valid_and_runtime_result_is_strict():
    for path in sorted((BASE / "00_meta/schemas").glob("p10-*.schema.json")):
        jsonschema.Draft7Validator.check_schema(json.loads(path.read_text()))
    driver = SimulatedP10WriteDriver()
    engine = P10ExecutionEngine(BASE, execution_enabled=True, driver=driver)
    plan = _prepare(engine); _approve(engine, plan)
    result = engine.execute(plan["plan_id"], state_probe=_probe, postcheck_runner=_post)
    schema = json.loads((BASE / "00_meta/schemas/p10-execution-result.schema.json").read_text())
    jsonschema.Draft7Validator(schema).validate(result)
