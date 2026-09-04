from pathlib import Path
import io
import json

import yaml

from core.tools.drivers.p7_live import PowerShellRemotingTransport, SnmpReadOnlyTransport, VerifiedHTTPTransport
from core.transports.preflight import LivePreflightValidator
from core.transports.registry import TransportRegistry
from core.transports.credentials import CredentialResolver
from core.api import server as api_server
from scripts.run_p7_authenticated_baseline import AuthenticatedBaselineRunner


ROOT = Path(__file__).resolve().parent.parent


def test_p7_catalog_covers_every_entity_and_is_disabled():
    registry = TransportRegistry(base_dir=ROOT)
    status = registry.public_status()
    assert status["total_entities"] == 48
    assert status["transport_implementation_coverage"] == 48
    assert status["transport_implementation_coverage_percent"] == 100.0
    assert len(status["drivers"]) == 7
    assert all(driver["default_enabled"] is False for driver in status["drivers"])
    assert status["live_enabled"] is False
    assert status["audit_mode"] == "IN_MEMORY_ONLY"
    assert status["retention"] == "NONE"
    assert status["persistence_enabled"] is False
    assert status["remediation_enabled"] is False
    bindings = status["credential_bindings"]
    assert bindings["total_bindings"] == 62
    assert bindings["active_bindings"] == 61
    assert bindings["owner_excluded_bindings"] == 1
    assert bindings["identity_pinned_bindings"] == 50
    assert bindings["host_key_pinned_bindings"] == 44
    assert bindings["tls_pinned_bindings"] == 6
    assert bindings["kerberos_bindings"] == 8
    assert bindings["permanent_mapping_complete"] is True
    assert bindings["operations_included"] is False
    assert bindings["environment_references_included"] is False


def test_target_conflicts_fail_closed_for_evidence():
    registry = TransportRegistry(base_dir=ROOT)
    plan = registry.target_plan("sw-cisco-core-01")
    assert plan["target_disposition"] == "CONFLICT_REQUIRES_IDENTITY_PROOF"
    assert plan["identity_proof_required"] is True
    assert plan["live_evidence_permitted"] is False


def test_all_device_preflight_is_owner_gated_and_trust_zero():
    calls = []
    def probe(target, port, timeout):
        calls.append((target, port, timeout))
        return True
    validator = LivePreflightValidator(base_dir=ROOT, probe=probe)
    blocked = validator.validate_all(owner_proceed=False)
    assert blocked["status"] == "NOT_RUN"
    assert calls == []
    result = validator.validate_all(owner_proceed=True)
    assert result["status"] == "COMPLETE"
    assert result["total_entities"] == 48
    assert all(item["trust_level"] == 0 and item["evidence_accepted"] is False for item in result["results"])
    assert result["persistence_attempted"] is False
    assert result["notifications_sent"] is False
    assert result["remediation_attempted"] is False


def test_protocol_drivers_reject_unsafe_or_untrusted_use():
    assert VerifiedHTTPTransport(target="127.0.0.1").request("POST", "/") ["status"] == "SCOPE_BLOCKED"
    powershell = PowerShellRemotingTransport()
    assert powershell.readiness(target="host", command="Restart-Service DNS", use_https=True, kerberos_identity=False)["status"] == "SCOPE_BLOCKED"
    assert powershell.readiness(target="host", command="Get-Service DNS", use_https=False, kerberos_identity=False)["status"] == "KERBEROS_OR_HTTPS_REQUIRED"
    assert SnmpReadOnlyTransport().readiness()["status"] == "SNMP_ENGINE_ID_NOT_CONFIGURED"


def test_p7_policy_is_sole_owner_and_disabled_at_rest():
    policy = yaml.safe_load((ROOT / "config/p7_live_policy.yaml").read_text(encoding="utf-8"))
    assert policy["enabled"] is False
    assert policy["approval_state"] == "OWNER_CONTROLLED"
    assert policy["owner_reference"] == "MNE-BRAIN-OWNER"
    assert policy["audit_mode"] == "IN_MEMORY_ONLY"
    assert policy["retention"] == "NONE"
    assert all(policy[key] is False for key in ("ticketing_enabled", "paging_enabled", "notifications_enabled", "automatic_assignment_enabled", "persistence_enabled", "remediation_enabled"))


def test_transport_api_is_redacted_and_non_connecting():
    handler = object.__new__(api_server.MNEBrainAPIHandler)
    handler.wfile = io.BytesIO()
    statuses = []
    handler._set_headers = lambda status_code=200, content_type="application/json": statuses.append(status_code)
    handler._handle_transports({})
    payload = json.loads(handler.wfile.getvalue().decode("utf-8"))
    serialized = json.dumps(payload, sort_keys=True).casefold()
    assert statuses == [200]
    assert payload["transport_implementation_coverage"] == payload["total_entities"] == 48
    assert payload["live_connection_attempted"] is False
    assert payload["credentials_included"] is False
    assert payload["raw_output_included"] is False
    assert payload["authenticated_validation_results_persisted"] is False
    assert payload["credential_bindings"]["active_bindings"] == 61
    assert payload["credential_bindings"]["owner_excluded_bindings"] == 1
    assert not any(marker in serialized for marker in ("password", "credential_reference", "canonical_target", "candidate_target", "172.23.", "10.60."))


def test_external_identity_pin_resolution_uses_ignored_source(tmp_path):
    external = tmp_path / "credentials.env"
    external.write_text(
        "MNE_TEST_HOST=192.0.2.10\n"
        "MNE_TEST_USERNAME=reader\n"
        "MNE_TEST_PASSWORD=not-a-real-secret\n"
        "MNE_TEST_SSH_HOSTKEY=ssh-ed25519 255 SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\n",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        f"MNE_FORTIGATE_CREDENTIAL_ENV_FILE={external}\n",
        encoding="utf-8",
    )
    resolver = CredentialResolver(tmp_path)
    assert resolver.value("MNE_TEST_SSH_HOSTKEY").startswith("ssh-ed25519 255 SHA256:")
    assert resolver.resolve(
        target="192.0.2.10",
        host_key="MNE_TEST_HOST",
        username_key="MNE_TEST_USERNAME",
        password_key="MNE_TEST_PASSWORD",
    ) == ("reader", "not-a-real-secret")


def test_authenticated_baseline_is_owner_gated_without_connections():
    result = AuthenticatedBaselineRunner(base_dir=ROOT).run(owner_proceed=False)
    assert result["status"] == "NOT_RUN"
    assert result["reason"] == "OWNER_PROCEED_REQUIRED"
    assert result["total_bindings"] == 61
    assert result["results"] == []


def test_exact_authenticated_scope_uses_one_transport_attempt(monkeypatch):
    runner = AuthenticatedBaselineRunner(base_dir=ROOT)
    monkeypatch.setattr(runner.credentials, "value", lambda key: "10.165.18.3" if key == "MNE_SWITCH_TULKARM_HOST" else "")
    calls = []
    def collect(binding, *, single_attempt=False):
        calls.append((binding["binding_id"], single_attempt))
        return runner._result(binding["binding_id"], "SUCCESS", attempted=True, output="bounded fixture")
    monkeypatch.setattr(runner, "_execute", collect)
    result = runner.run_exact(owner_proceed=True, binding_id="p7-switch-tulkarm", target="10.165.18.3", check_id="ip_interface_brief")
    assert result["status"] == "COMPLETE" and result["status_counts"] == {"SUCCESS": 1}
    assert calls == [("p7-switch-tulkarm", True)]


def test_credential_scope_can_be_separate_from_asset_identity(monkeypatch, tmp_path):
    """A shared reader account must not make a per-device host-key pin optional."""
    runner = AuthenticatedBaselineRunner(base_dir=ROOT)
    runner.plink = tmp_path / "plink.exe"
    runner.plink.write_bytes(b"fixture")
    values = {
        "MNE_DEVICE_HOST": "192.0.2.40",
        "MNE_DEVICE_SSH_HOSTKEY": "ssh-ed25519 255 SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        "MNE_SHARED_USERNAME": "reader",
        "MNE_SHARED_PASSWORD": "fixture-password",
    }
    monkeypatch.setattr(runner.credentials, "value", lambda key: values.get(key, ""))
    observed = []

    class Completed:
        returncode = 0
        stdout = "Version: fixture\n"
        stderr = ""

    def run(arguments, **kwargs):
        observed.extend(arguments)
        return Completed()

    monkeypatch.setattr("scripts.run_p7_authenticated_baseline.subprocess.run", run)
    result = runner._ssh({
        "binding_id": "p7-fixture", "env_prefix": "MNE_DEVICE", "credential_env_prefix": "MNE_SHARED",
        "target": "192.0.2.40", "check_id": "version", "operation": "show version", "platform": "cisco_iosxe",
    }, allow_interactive_fallback=False)
    assert result["status"] == "SUCCESS"
    assert observed[observed.index("-l") + 1] == "reader"
