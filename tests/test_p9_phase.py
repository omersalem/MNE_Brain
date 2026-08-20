from datetime import datetime, timedelta, timezone
from io import BytesIO
import hashlib
import json
from pathlib import Path
import subprocess

import pytest
import yaml

from core.api import server as api_server
from core.troubleshooting.p9_collector import P9LiveCollector
from core.troubleshooting.p9_engine import P9DiagnosticEngine
from core.troubleshooting.p9_live_session import P9LiveSession
from core.troubleshooting.p9_normalizers import normalize_output
from core.transports import specialized
from core.transports.specialized import FMCRestTransport, KerberosPowerShellTransport, PinnedJSONHTTPSClient, VCenterRestTransport


ROOT = Path(__file__).resolve().parent.parent


def _evidence(check, *, when=None):
    material = f"{check['binding_id']}|{check['check_id']}"
    return {"evidence_id": "ev-" + hashlib.sha256(material.encode()).hexdigest()[:12], "binding_id": check["binding_id"], "check_id": check["check_id"], "collected_at": (when or datetime.now(timezone.utc)).isoformat(), "verification_status": "live_verified", "trust_level": 5, "outcome": "SUCCESS", "summary": "Normalized attributable evidence.", "observations": {"signal": 1}, "output_sha256_prefix": hashlib.sha256(material.encode()).hexdigest()[:16]}


def test_p9_catalog_policy_and_public_status_are_safe():
    engine = P9DiagnosticEngine(ROOT)
    status = engine.status()
    assert status["scenario_count"] == 8 and status["check_count"] == 30
    assert status["live_enabled"] is False and status["operations_included"] is False
    assert status["automatic_diagnosis_enabled"] is False
    serialized = json.dumps(status).casefold()
    assert "tmsh" not in serialized and "get system" not in serialized and "password" not in serialized
    policy = yaml.safe_load((ROOT / "config/p9_troubleshooting_policy.yaml").read_text(encoding="utf-8"))
    assert policy["owner_reference"] == "MNE-BRAIN-OWNER"
    assert policy["maximum_bindings_per_scope"] == 3 and policy["maximum_checks_per_session"] == 4
    assert all(policy[key] is False for key in ("enabled", "ticketing_enabled", "paging_enabled", "notifications_enabled", "automatic_assignment_enabled", "persistence_enabled", "remediation_enabled", "external_ai_enabled", "automatic_diagnosis_enabled", "automatic_canonical_promotion_enabled"))


@pytest.mark.parametrize("scenario,binding", [
    ("p9-branch-outage", "p7-fortigate-nablus"), ("p9-vpn-access", "p7-fortigate-edge"),
    ("p9-web-publishing", "p7-f5"), ("p9-dns-ad", "p7-ad-primary"),
    ("p9-exchange", "p7-exchange-primary"), ("p9-vmware", "p7-vcenter"),
    ("p9-firewall-security", "p7-ftd"), ("p9-storage-backup-switching", "p7-fujitsu-sw1"),
])
def test_all_p9_families_plan_exact_bounded_checks(scenario, binding):
    result = P9DiagnosticEngine(ROOT).plan({"scenario_id": scenario, "binding_id": binding, "symptom": "reported issue"})
    assert result["status"] == "EVIDENCE_REQUIRED"
    assert 1 <= result["metrics"]["bindings"] <= 3
    assert result["next_check"] == result["candidate_checks"][0]
    assert result["root_cause"] is None and result["confidence"] == 0
    assert result["metrics"]["handoff_chars"] <= 6000 and result["metrics"]["handoff_token_estimate"] <= 1500
    assert not any(result["safety"].values())
    assert all("operation" not in item for item in result["candidate_checks"])


def test_p9_scope_and_mutation_boundaries_fail_closed():
    engine = P9DiagnosticEngine(ROOT)
    with pytest.raises(ValueError, match="scenario_id"):
        engine.plan({"scenario_id": "p9-unknown", "binding_id": "p7-f5"})
    with pytest.raises(ValueError, match="not permitted"):
        engine.plan({"scenario_id": "p9-vpn-access", "binding_id": "p7-f5"})
    with pytest.raises(ValueError, match="owner-excluded"):
        engine.plan({"scenario_id": "p9-storage-backup-switching", "binding_id": "p7-switch-ramallah-gold"})
    assert engine.WRITE_TOKENS.search("restart service")


def test_p9_normalizers_return_only_compact_signals():
    observations, summary = normalize_output("fortigate_interfaces", "== [port1]\nstatus: up\n== [port2]\nstatus: down\n")
    assert observations["sections"] == 2 and observations["up"] == 1 and observations["down"] == 1
    assert "port1" not in json.dumps(observations) and len(summary) <= 240


def test_p9_rest_normalizers_aggregate_without_identifiers():
    observations, _ = normalize_output("rest_inventory", '{"value":[{"host":"host-1","name":"private-a","connection_state":"CONNECTED"},{"host":"host-2","name":"private-b","connection_state":"DISCONNECTED"}]}')
    fmc, _ = normalize_output("fmc_json", '{"items":[{"id":"secret-id","name":"private-ftd","status":"DEPLOYED"}]}')
    serialized = json.dumps({"vcenter": observations, "fmc": fmc})
    assert observations["object_count"] == 2 and observations["connected"] == 1 and observations["disconnected"] == 1
    assert fmc["object_count"] == 1 and fmc["managed_objects_present"] is True
    assert "private" not in serialized and "secret-id" not in serialized and "host-1" not in serialized


def test_specialized_transports_fail_closed_before_network(tmp_path):
    assert PinnedJSONHTTPSClient("example.invalid", "bad-pin").request("GET", "/api")["status"] == "TARGET_OR_IDENTITY_NOT_CONFIGURED"
    assert VCenterRestTransport(tmp_path).collect("GET /unsafe")["status"] == "SCOPE_BLOCKED"
    assert FMCRestTransport(tmp_path).collect("POST /api/fmc_platform/v1/auth/generatetoken")["status"] == "SCOPE_BLOCKED"


def test_shared_credential_kerberos_transport_keeps_secret_out_of_result(tmp_path):
    external = tmp_path / "credential-source.env"
    external.write_text("MNE_AD_USERNAME=domain-reader\nMNE_AD_PASSWORD=test-only-secret\n", encoding="utf-8")
    (tmp_path / ".env").write_text(f"MNE_FORTIGATE_CREDENTIAL_ENV_FILE={external}\n", encoding="utf-8")
    calls = []
    def runner(*args, **kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(args[0], 0, stdout='{"total":3,"running":3}', stderr="")
    result = KerberosPowerShellTransport(tmp_path, runner).collect(prefix="MNE_AD", target="MNE-DC2.mne.gov", operation="Get-Service DNS,NTDS,Kdc")
    assert result["status"] == "SUCCESS" and result["connection_attempted"] is True
    assert "test-only-secret" not in json.dumps(result)
    assert calls[0]["env"]["MNE_TRANSPORT_USERNAME"] == "domain-reader"
    json_obs, _ = normalize_output("windows_json", '{"total":3,"running":2,"stopped":1}')
    assert json_obs == {"json_valid": True, "total": 3, "running": 2, "stopped": 1}
    ports, _ = normalize_output("linux_ports", "LISTEN 0 128 0.0.0.0:22\nLISTEN 0 128 0.0.0.0:80")
    assert ports["expected_22"] is True and ports["expected_80"] is True


def test_p9_evidence_and_reasoning_assessment_are_attributable():
    engine = P9DiagnosticEngine(ROOT)
    request = {"scenario_id": "p9-dns-ad", "binding_id": "p7-ad-primary", "symptom": "dns down"}
    first = engine.plan(request)["next_check"]
    evidence = _evidence(first)
    state = engine.plan({**request, "evidence": [evidence]})
    assert state["accepted_evidence"] == [evidence] and state["status"] == "MORE_EVIDENCE_AVAILABLE"
    assessment = {"root_cause": "Core identity service state is inconsistent.", "confidence": 0.96, "evidence_refs": [evidence["evidence_id"]], "unknowns": ["Secondary DC state"], "action": "OWNER_REVIEW_REQUIRED"}
    stopped = engine.plan({**request, "evidence": [evidence], "reasoning_assessment": assessment})
    assert stopped["status"] == "STOP_EARLY_EVIDENCE_BOUND" and stopped["stop_early"] is True
    with pytest.raises(ValueError, match="unaccepted"):
        engine.plan({**request, "evidence": [evidence], "reasoning_assessment": {**assessment, "evidence_refs": ["forged"]}})
    stale = _evidence(first, when=datetime.now(timezone.utc) - timedelta(hours=1))
    raw = {**evidence, "evidence_id": "raw", "raw_output": "forbidden"}
    rejected = engine.plan({**request, "evidence": [stale, raw]})
    assert len(rejected["rejected_evidence"]) == 2 and not rejected["accepted_evidence"]


def test_p9_live_session_is_owner_gated_and_adaptive():
    calls = []
    def collector(**kwargs):
        calls.append(kwargs["check_id"])
        check = next(item for item in P9DiagnosticEngine(ROOT).resolved_checks(kwargs["scenario_id"], kwargs["primary_binding"]) if item["check_id"] == kwargs["check_id"])
        return {"status": "SUCCESS", "binding_id": check["binding_id"], "check_id": check["check_id"], "connection_attempted": True, "evidence": _evidence(check)}
    def reason(handoff):
        evidence_id = handoff["accepted_evidence"][0]["evidence_id"]
        return {"root_cause": "Injected test hypothesis.", "confidence": 0.97, "evidence_refs": [evidence_id], "unknowns": [], "action": "OWNER_REVIEW_REQUIRED"}
    request = {"scenario_id": "p9-vpn-access", "binding_id": "p7-fortigate-edge", "symptom": "vpn failed"}
    session = P9LiveSession(ROOT, collector, reason)
    assert session.run(request, owner_proceed=False)["status"] == "NOT_RUN" and calls == []
    result = session.run(request, owner_proceed=True)
    assert result["status"] == "STOP_EARLY_EVIDENCE_BOUND" and len(calls) == 1
    assert result["safety"]["live_connection_attempted"] is True
    assert result["live_session"]["policy_restored_to_disabled"] is True


def test_p9_collector_rejects_missing_owner_or_check_without_connection():
    collector = P9LiveCollector(ROOT)
    blocked = collector.collect(scenario_id="p9-vpn-access", primary_binding="p7-fortigate-edge", check_id="p9_vpn_sessions", owner_proceed=False)
    assert blocked["status"] == "NOT_RUN" and blocked["connection_attempted"] is False
    unknown = collector.collect(scenario_id="p9-vpn-access", primary_binding="p7-fortigate-edge", check_id="p9_unknown", owner_proceed=True)
    assert unknown["status"] == "NOT_RUN" and unknown["connection_attempted"] is False


def test_p9_collector_recovers_text_or_bytes_received_before_timeout():
    text_timeout = subprocess.TimeoutExpired(["plink"], 1, output="interface up\n")
    byte_timeout = subprocess.TimeoutExpired(["plink"], 1, output=b"interface down\n")
    assert P9LiveCollector._timeout_output(text_timeout) == "interface up\n"
    assert P9LiveCollector._timeout_output(byte_timeout) == "interface down\n"


def test_p9_network_normalizers_reject_prompt_only_signal():
    weak, _ = normalize_output("network_interfaces", "device#\n")
    strong, _ = normalize_output("network_interfaces", "GigabitEthernet0/0 up up\n")
    compact_identity, _ = normalize_output("identity_status", "Firmware version 1.2.3\n")
    bare_version, _ = normalize_output("identity_status", "1.3.68\n")
    assert weak["signal_quality"] == "LOW" and strong["signal_quality"] == "HIGH"
    assert compact_identity["signal_quality"] == "HIGH" and compact_identity["firmware"] == 1
    assert bare_version["signal_quality"] == "HIGH" and bare_version["version_number_present"] is True


def test_p9_api_status_and_plan_are_nonconnecting_and_redacted():
    for method, payload in (("_handle_p9_status", None), ("_handle_p9_plan", {"scenario_id": "p9-vpn-access", "binding_id": "p7-fortigate-edge", "symptom": "vpn down", "evidence": [{"raw_output": "ignored"}]})):
        handler = object.__new__(api_server.MNEBrainAPIHandler)
        handler.wfile, statuses = BytesIO(), []
        handler._set_headers = lambda status_code=200, content_type="application/json": statuses.append(status_code)
        getattr(handler, method)(payload) if payload is not None else getattr(handler, method)()
        result = json.loads(handler.wfile.getvalue().decode())
        assert statuses == [200]
        serialized = json.dumps(result).casefold()
        assert "ignored" not in serialized and "password" not in serialized and "tmsh" not in serialized and "get system" not in serialized
        assert result.get("live_connection_attempted", result.get("safety", {}).get("live_connection_attempted")) is False
