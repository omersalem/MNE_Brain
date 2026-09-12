from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
from pathlib import Path

import pytest
import yaml

from core.api import server as api_server
from core.troubleshooting.engine import P8TroubleshootingEngine
from core.troubleshooting.live_session import P8LiveSession


ROOT = Path(__file__).resolve().parent.parent


def test_p8_catalog_and_policy_are_complete_and_disabled():
    engine = P8TroubleshootingEngine(ROOT)
    status = engine.status()
    assert status["scenario_count"] == 8
    assert status["reconciliation_count"] == 63
    assert set(status["scenario_families"]) == {"branch_outage", "vpn", "web_publishing", "dns_ad", "exchange", "vmware", "firewall_security", "storage_backup_switching"}
    assert status["live_enabled"] is False
    assert status["audit_mode"] == "IN_MEMORY_ONLY"
    assert status["retention"] == "NONE"
    assert all(item["canonical_promotion_allowed"] is False for item in engine.reconciliations.values())
    policy = yaml.safe_load((ROOT / "config/p8_troubleshooting_policy.yaml").read_text(encoding="utf-8"))
    assert policy["owner_reference"] == "MNE-BRAIN-OWNER"
    assert all(policy[key] is False for key in ("enabled", "ticketing_enabled", "paging_enabled", "notifications_enabled", "automatic_assignment_enabled", "persistence_enabled", "remediation_enabled", "external_ai_enabled"))


@pytest.mark.parametrize("scenario,binding,symptom", [
    ("p8-branch-outage", "p7-fortigate-nablus", "branch down"),
    ("p8-vpn-access", "p7-fortigate-edge", "VPN login failed"),
    ("p8-web-publishing", "p7-f5", "website down"),
    ("p8-dns-ad", "p7-ad-primary", "DNS issue"),
    ("p8-exchange", "p7-exchange-primary", "email unavailable"),
    ("p8-vmware", "p7-vcenter", "vCenter down"),
    ("p8-firewall-security", "p7-ftd", "traffic blocked"),
    ("p8-storage-backup-switching", "p7-fujitsu-sw1", "fabric issue"),
])
def test_p8_all_scenario_families_plan_without_side_effects(scenario, binding, symptom):
    result = P8TroubleshootingEngine(ROOT).plan({"scenario_id": scenario, "binding_id": binding, "symptom": symptom})
    assert result["status"] == "EVIDENCE_REQUIRED"
    assert 1 <= len(result["planned_checks"]) <= 3
    assert result["root_cause"] is None
    assert result["metrics"]["handoff_chars"] <= 6000
    assert result["metrics"]["evidence_token_estimate"] <= 1500
    assert not any(result["safety"].values())


def test_p8_rejects_unknown_wrong_or_excluded_scope():
    engine = P8TroubleshootingEngine(ROOT)
    with pytest.raises(ValueError, match="scenario_id"):
        engine.plan({"scenario_id": "unknown", "binding_id": "p7-f5"})
    with pytest.raises(ValueError, match="not permitted"):
        engine.plan({"scenario_id": "p8-vpn-access", "binding_id": "p7-f5"})
    with pytest.raises(ValueError, match="owner-excluded"):
        engine.plan({"scenario_id": "p8-storage-backup-switching", "binding_id": "p7-switch-ramallah-gold"})


def test_p8_accepts_only_fresh_attributable_trust_five_evidence():
    engine = P8TroubleshootingEngine(ROOT)
    request = {"scenario_id": "p8-dns-ad", "binding_id": "p7-ad-primary", "symptom": "DNS down"}
    good = {"evidence_id": "ev-good", "binding_id": "p7-ad-primary", "check_id": "identity_services", "collected_at": datetime.now(timezone.utc).isoformat(), "verification_status": "live_verified", "trust_level": 5, "outcome": "SUCCESS", "summary": "Authenticated read-only baseline succeeded."}
    result = engine.plan({**request, "evidence": [good]})
    assert result["status"] == "LIVE_EVIDENCE_ACCEPTED"
    assert result["accepted_evidence"] == [good]
    stale = {**good, "evidence_id": "ev-stale", "collected_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}
    wrong = {**good, "evidence_id": "ev-wrong", "binding_id": "p7-f5"}
    unsafe = {**good, "evidence_id": "ev-raw", "raw_output": "secret"}
    rejected = engine.plan({**request, "evidence": [stale, wrong, unsafe]})
    assert rejected["status"] == "EVIDENCE_REQUIRED"
    assert len(rejected["rejected_evidence"]) == 3


def test_p8_live_session_is_owner_gated_and_uses_exact_selected_scope():
    calls = []
    def collector(*, owner_proceed, binding_ids):
        calls.append((owner_proceed, binding_ids))
        return {"status": "COMPLETE", "results": [{"binding_id": item, "status": "SUCCESS", "connection_attempted": True} for item in binding_ids]}
    session = P8LiveSession(ROOT, collector)
    request = {"scenario_id": "p8-exchange", "binding_id": "p7-exchange-primary", "symptom": "email down"}
    blocked = session.run(request, owner_proceed=False)
    assert blocked["status"] == "NOT_RUN" and calls == []
    result = session.run(request, owner_proceed=True)
    assert calls == [(True, ["p7-exchange-primary", "p7-exchange-ps", "p7-ad-primary"])]
    assert result["status"] == "LIVE_EVIDENCE_ACCEPTED"
    assert result["live_session"]["policy_restored_to_disabled"] is True
    assert result["live_session"]["raw_output_included"] is False


def test_p8_api_is_planning_only_and_redacted():
    handler = object.__new__(api_server.MNEBrainAPIHandler)
    handler.wfile = BytesIO()
    statuses = []
    handler._set_headers = lambda status_code=200, content_type="application/json": statuses.append(status_code)
    handler._handle_p8_plan({"scenario_id": "p8-vpn-access", "binding_id": "p7-fortigate-edge", "symptom": "vpn down", "evidence": [{"raw_output": "ignored"}]})
    payload = json.loads(handler.wfile.getvalue().decode())
    assert statuses == [200]
    assert payload["safety"]["live_connection_attempted"] is False
    serialized = json.dumps(payload).casefold()
    assert "ignored" not in serialized
    assert payload["safety"]["raw_output_included"] is False
    assert "password" not in serialized

    status_handler = object.__new__(api_server.MNEBrainAPIHandler)
    status_handler.wfile = BytesIO()
    status_codes = []
    status_handler._set_headers = lambda status_code=200, content_type="application/json": status_codes.append(status_code)
    status_handler._handle_p8_status()
    status_payload = json.loads(status_handler.wfile.getvalue().decode())
    assert status_codes == [200]
    assert status_payload["status"] == "IMPLEMENTED_DISABLED_AT_REST"
    assert status_payload["live_connection_attempted"] is False


def test_p7_selected_runner_rejects_broad_or_unknown_scope_without_connecting():
    from scripts.run_p7_authenticated_baseline import AuthenticatedBaselineRunner
    runner = AuthenticatedBaselineRunner(ROOT)
    assert runner.run_selected(owner_proceed=True, binding_ids=[])["reason"] == "EXACT_ACTIVE_SCOPE_REQUIRED"
    assert runner.run_selected(owner_proceed=True, binding_ids=["p7-switch-ramallah-gold"])["reason"] == "EXACT_ACTIVE_SCOPE_REQUIRED"
    assert runner.run_selected(owner_proceed=False, binding_ids=["p7-f5"])["reason"] == "OWNER_PROCEED_REQUIRED"
