import json
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path
from core.api.server import MNEBrainAPIHandler


class DummyHandler(MNEBrainAPIHandler):
    """Subclass of MNEBrainAPIHandler for unit testing without live HTTP sockets."""

    def __init__(self):
        self.sent_status = None
        self.sent_headers = {}
        self.response_body = b""
        self.wfile = MagicMock()
        self.wfile.write.side_effect = lambda data: setattr(self, "response_body", self.response_body + data)

    def _set_headers(self, status_code=200, content_type="application/json", extra_headers=None, content_length=None):
        self.sent_status = status_code
        self.sent_headers["Content-Type"] = content_type
        if extra_headers:
            self.sent_headers.update(extra_headers)

    def _json_response(self, status_code, payload, extra_headers=None):
        self._set_headers(status_code, "application/json; charset=utf-8", extra_headers=extra_headers)
        raw = json.dumps(payload).encode("utf-8")
        self.response_body = raw


def test_api_security_agent_status():
    handler = DummyHandler()
    handler._handle_security_agent_status()

    assert handler.sent_status == 200
    data = json.loads(handler.response_body.decode("utf-8"))

    assert "config" in data
    assert "schedule_time" in data["config"]
    assert "recipients" in data["config"]
    assert "devices" in data
    assert len(data["devices"]) == 7
    assert "reports" in data


def test_api_security_agent_config_update(monkeypatch, tmp_path):
    handler = DummyHandler()

    test_cfg_path = tmp_path / "test_sec_cfg.json"
    from core.security_review.config import SecurityAgentConfig
    monkeypatch.setattr(SecurityAgentConfig, "__init__", lambda self, config_path=None: setattr(self, "config_path", test_cfg_path) or setattr(self, "reports_dir", tmp_path))
    monkeypatch.setattr(SecurityAgentConfig, "sync_windows_task", lambda self, t, e: {"synced": True})

    payload = {
        "schedule_time": "06:45",
        "schedule_enabled": True,
        "recipients": ["new-admin@mne.gov.ps", "sec-team@mne.gov.ps"],
    }
    handler._handle_security_agent_config_post(payload)

    assert handler.sent_status == 200
    data = json.loads(handler.response_body.decode("utf-8"))

    assert data["config"]["schedule_time"] == "06:45"
    assert data["config"]["schedule_enabled"] is True
    assert "new-admin@mne.gov.ps" in data["config"]["recipients"]


def test_api_security_agent_config_invalid_email():
    handler = DummyHandler()
    payload = {"recipients": ["not-a-valid-email"]}
    handler._handle_security_agent_config_post(payload)

    assert handler.sent_status == 400
    data = json.loads(handler.response_body.decode("utf-8"))
    assert "error" in data


def test_api_security_agent_test_email(monkeypatch):
    handler = DummyHandler()

    from core.security_review.reporter import SecurityReporter
    monkeypatch.setattr(SecurityReporter, "send_test_email", lambda self, recipients=None: (True, "Test email sent successfully"))

    handler._handle_security_agent_test_email_post({})
    assert handler.sent_status == 200
    data = json.loads(handler.response_body.decode("utf-8"))
    assert data["success"] is True


def test_api_security_agent_reports_404_when_missing(monkeypatch):
    handler = DummyHandler()

    from core.security_review.config import SecurityAgentConfig
    monkeypatch.setattr(SecurityAgentConfig, "get_latest_reports", lambda self: {
        "html": {"available": False},
        "pdf": {"available": False},
    })

    handler._handle_security_agent_report_html()
    assert handler.sent_status == 404

    handler_pdf = DummyHandler()
    handler_pdf._handle_security_agent_report_pdf()
    assert handler_pdf.sent_status == 404


def test_api_security_agent_runs_endpoints(monkeypatch, tmp_path):
    from core.security_review.run_store import SecurityReviewRunStore
    from core.security_review.service import SecurityReviewService
    from core.security_review.jobs import SecurityReviewJobManager
    from core.connectors.security.models import CollectorResult, CollectorStatus

    test_store = SecurityReviewRunStore(tmp_path / "runs")
    test_jm = SecurityReviewJobManager()

    class MockCol:
        device_name = "MockDevice"
        def collect_logs(self, hours_back=24):
            return CollectorResult(device_name="MockDevice", status=CollectorStatus.SUCCESS, events=[], collection_duration_seconds=0.01)

    mock_registry = {"fortigate_core": MockCol()}
    test_svc = SecurityReviewService(
        run_store=test_store,
        job_manager=test_jm,
        collector_registry=mock_registry,
    )

    import core.api.server as srv
    monkeypatch.setattr(srv, "security_review_run_store", test_store)
    monkeypatch.setattr(srv, "security_review_job_manager", test_jm)
    monkeypatch.setattr(srv, "security_review_service", test_svc)

    # 1. Start run via POST /api/v2/security-agent/runs
    handler = DummyHandler()
    payload = {
        "mode": "QUICK",
        "collector_ids": ["fortigate_core"],
        "hours_back": 1.0,
        "analysis_engine": "NONE",
        "send_email": False,
        "report_formats": ["JSON"],
    }
    handler._handle_security_agent_runs_post(payload)
    assert handler.sent_status == 202
    data = json.loads(handler.response_body.decode("utf-8"))
    assert "run_id" in data
    run_id = data["run_id"]

    # 2. List runs via GET /api/v2/security-agent/runs
    handler_list = DummyHandler()
    handler_list._handle_security_agent_runs_get()
    assert handler_list.sent_status == 200
    list_data = json.loads(handler_list.response_body.decode("utf-8"))
    assert "runs" in list_data
    assert any(r["run_id"] == run_id for r in list_data["runs"])

    # 3. Get single run via GET /api/v2/security-agent/runs/{run_id}
    handler_get = DummyHandler()
    handler_get._handle_security_agent_run_get(run_id)
    assert handler_get.sent_status == 200
    single_data = json.loads(handler_get.response_body.decode("utf-8"))
    assert single_data["run_id"] == run_id

    # 4. Cancel run via POST /api/v2/security-agent/runs/{run_id}/cancel
    handler_cancel = DummyHandler()
    handler_cancel._handle_security_agent_run_cancel_post(run_id)
    assert handler_cancel.sent_status == 200
    cancel_data = json.loads(handler_cancel.response_body.decode("utf-8"))
    assert cancel_data["run_id"] == run_id

    # 5. Retry run via POST /api/v2/security-agent/runs/{run_id}/retry
    handler_retry = DummyHandler()
    handler_retry._handle_security_agent_run_retry_post(run_id, {"only_failed": False})
    assert handler_retry.sent_status == 202
    retry_data = json.loads(handler_retry.response_body.decode("utf-8"))
    assert retry_data["retry_of"] == run_id


def test_api_security_agent_run_compatibility_post(monkeypatch):
    handler = DummyHandler()
    mock_pipeline_result = {
        "success": True,
        "incidents": [],
        "collectors": [],
        "email_sent": False,
        "html_path": "test.html",
        "pdf_path": "test.pdf",
    }
    with patch("core.security_review.cli.run_security_pipeline", return_value=mock_pipeline_result):
        handler._handle_security_agent_run_post({"dry_run": True})
        assert handler.sent_status == 200
        data = json.loads(handler.response_body.decode("utf-8"))
        assert data["success"] is True
        assert data["html_path"] == "test.html"


def test_api_security_agent_incident_endpoints(monkeypatch, tmp_path):
    from core.security_review.run_store import SecurityReviewRunStore
    from core.security_review.incidents import IncidentRecord
    import core.api.server as srv

    test_store = SecurityReviewRunStore(tmp_path / "runs")
    monkeypatch.setattr(srv, "security_review_run_store", test_store)

    # Seed an incident record
    test_record = IncidentRecord(
        fingerprint="inc-endpoint-test",
        display_id="MNE-SEC-20260909-99",
        title="SQLi on Portal",
        category="WAF_EXPLOIT",
        signature_family="sqli",
        source_device="F5 BIG-IP",
        attacker_identity="198.51.100.44",
        target_identity="/portal/login.aspx",
        current_severity="HIGH",
        peak_severity="HIGH",
        lifecycle_state="NEW",
        event_count=5,
    )
    test_store.save_incident_record(test_record)

    # 1. GET /api/v2/security-agent/incidents
    handler_list = DummyHandler()
    handler_list._handle_security_agent_incidents_get()
    assert handler_list.sent_status == 200
    list_data = json.loads(handler_list.response_body.decode("utf-8"))
    assert "incidents" in list_data
    assert list_data["total"] >= 1
    assert any(i["fingerprint"] == "inc-endpoint-test" for i in list_data["incidents"])

    # 2. GET /api/v2/security-agent/incidents/{fingerprint}
    handler_get = DummyHandler()
    handler_get._handle_security_agent_incident_get("inc-endpoint-test")
    assert handler_get.sent_status == 200
    single_data = json.loads(handler_get.response_body.decode("utf-8"))
    assert single_data["fingerprint"] == "inc-endpoint-test"
    assert single_data["title"] == "SQLi on Portal"

    # 2b. GET 404 for non-existent fingerprint
    handler_404 = DummyHandler()
    handler_404._handle_security_agent_incident_get("inc-non-existent")
    assert handler_404.sent_status == 404

    # 3. POST /api/v2/security-agent/incidents/{fingerprint}/status
    handler_status = DummyHandler()
    handler_status._handle_security_agent_incident_status_post(
        "inc-endpoint-test",
        {"status": "INVESTIGATING", "author": "analyst-dan", "note": "Triaging WAF logs"},
    )
    assert handler_status.sent_status == 200
    status_data = json.loads(handler_status.response_body.decode("utf-8"))
    assert status_data["lifecycle_state"] == "INVESTIGATING"
    assert any("Triaging WAF logs" in n["note"] for n in status_data["analyst_notes"])

    # 4. POST /api/v2/security-agent/incidents/{fingerprint}/notes
    handler_notes = DummyHandler()
    handler_notes._handle_security_agent_incident_notes_post(
        "inc-endpoint-test",
        {"note": "Attacker IP belongs to digital ocean AS", "author": "analyst-dan"},
    )
    assert handler_notes.sent_status == 200
    notes_data = json.loads(handler_notes.response_body.decode("utf-8"))
    assert any("digital ocean" in n["note"] for n in notes_data["analyst_notes"])

    # 5. GET /api/v2/security-agent/incidents/{fingerprint}/timeline
    handler_tl = DummyHandler()
    handler_tl._handle_security_agent_incident_timeline_get("inc-endpoint-test")
    assert handler_tl.sent_status == 200
    tl_data = json.loads(handler_tl.response_body.decode("utf-8"))
    assert tl_data["fingerprint"] == "inc-endpoint-test"
    assert len(tl_data["timeline"]) >= 3  # FIRST_SEEN, STATUS_CHANGE, NOTE


def test_api_security_agent_incident_resolve_identity_post(monkeypatch, tmp_path):
    from core.security_review.run_store import SecurityReviewRunStore
    from core.security_review.incidents import IncidentRecord
    from core.security_review.identity_enrichment import (
        LocalAttackerIdentityResolver,
        EventNativeIdentityAdapter,
        AttackerAttribution,
    )
    import core.api.server as srv

    test_store = SecurityReviewRunStore(tmp_path / "runs")
    monkeypatch.setattr(srv, "security_review_run_store", test_store)

    class DummySecService:
        def __init__(self):
            self.identity_resolver = LocalAttackerIdentityResolver(
                adapters=[EventNativeIdentityAdapter()]
            )

    dummy_svc = DummySecService()
    monkeypatch.setattr(srv, "security_review_service", dummy_svc)

    # 1. 404 on missing incident
    handler_404 = DummyHandler()
    handler_404._handle_security_agent_incident_resolve_identity_post("nonexistent", {})
    assert handler_404.sent_status == 404

    # 2. Seed run events with multiple entries
    run_id = "run-api-resolve-001"
    raw_events = [
        {
            "event_id": "ev-scoped-1",
            "timestamp": "2026-09-09T10:00:00Z",
            "source_device": "FortiGate",
            "category": "ANOMALY",
            "threat_name": "Port Scan",
            "attacker_ip": "10.20.30.40",
            "source_hostname": "PC-FINANCE-01",
            "authenticated_source_user": "salim_finance",
        },
        {
            "event_id": "ev-wrong-ip",
            "timestamp": "2026-09-09T10:00:00Z",
            "source_device": "FortiGate",
            "category": "ANOMALY",
            "threat_name": "Port Scan",
            "attacker_ip": "10.20.30.99",
            "source_hostname": "PC-WRONG-IP",
            "authenticated_source_user": "wrong_user",
        },
        {
            "event_id": "ev-unsupported-id",
            "timestamp": "2026-09-09T10:00:00Z",
            "source_device": "FortiGate",
            "category": "ANOMALY",
            "threat_name": "Port Scan",
            "attacker_ip": "10.20.30.40",
            "source_hostname": "PC-WRONG-SCOPE",
            "authenticated_source_user": "wrong_scope_user",
        },
    ]
    test_store.save_events(run_id, raw_events)

    incident = IncidentRecord(
        fingerprint="inc-resolve-test-01",
        display_id="MNE-SEC-20260909-42",
        title="Internal Anomaly",
        category="ANOMALY",
        signature_family="port_scan",
        source_device="FortiGate",
        attacker_identity="10.20.30.40",
        target_identity="10.0.0.1",
        current_severity="HIGH",
        peak_severity="HIGH",
        lifecycle_state="NEW",
        event_count=1,
        run_references=[run_id],
        supporting_event_ids=["ev-scoped-1"],
        first_seen="2026-09-09T10:00:00Z",
        last_seen="2026-09-09T10:00:00Z",
    )
    test_store.save_incident_record(incident)

    # 3. Successful resolution with scoped event
    handler_ok = DummyHandler()
    handler_ok._handle_security_agent_incident_resolve_identity_post("inc-resolve-test-01", {})
    assert handler_ok.sent_status == 200
    res_data = json.loads(handler_ok.response_body.decode("utf-8"))
    assert res_data["attacker_attribution"] is not None
    attr = res_data["attacker_attribution"]
    assert attr["pc_name"] == "PC-FINANCE-01"
    assert attr["username"] == "salim_finance"
    assert attr["status"] == "RESOLVED"
    assert len(attr.get("attribution_history", [])) == 1

    # 4. Non-downgrade test: mock resolver returning NOT_FOUND
    class EmptyResolver:
        def resolve_attacker_identity(self, *args, **kwargs):
            return AttackerAttribution(
                ip_address=kwargs.get("ip_address", "10.20.30.40"),
                status="NOT_FOUND",
                confidence="NONE",
                confidence_score=0,
                successful_sources=[],
            )

    dummy_svc.identity_resolver = EmptyResolver()
    handler_downgrade = DummyHandler()
    handler_downgrade._handle_security_agent_incident_resolve_identity_post("inc-resolve-test-01", {})
    assert handler_downgrade.sent_status == 200
    res_data2 = json.loads(handler_downgrade.response_body.decode("utf-8"))
    attr2 = res_data2["attacker_attribution"]
    assert attr2["pc_name"] == "PC-FINANCE-01"
    assert attr2["username"] == "salim_finance"
    assert attr2["status"] == "RESOLVED"
    assert len(attr2.get("attribution_history", [])) == 2
    assert attr2["attribution_history"][-1]["status"] == "NOT_FOUND"
    assert attr2["attribution_history"][-1]["diagnostic"] == "Preserved prior higher-confidence attribution."


def test_api_security_agent_analysis_report(monkeypatch):
    import core.api.server as srv

    handler_404 = DummyHandler()
    monkeypatch.setattr(srv.security_review_service.ai_analyzer, "get_analysis", lambda aid: None)
    handler_404._handle_security_agent_analysis_report_get("nonexistent-an", {"format": ["html"]})
    assert handler_404.sent_status == 404

    sample_analysis = {
        "analysis_id": "an-api-test-01",
        "engine": "ANTIGRAVITY",
        "model": "gemini-2.5-pro",
        "status": "COMPLETED",
        "confidence": 0.95,
        "run_id": "run-sec-20260912-001",
        "plain_summary": "Active brute force observed.",
        "ranked_hypotheses": [
            {"hypothesis": "External credential stuffing", "likelihood": "HIGH", "explanation": "Failed auths"}
        ],
        "affected_systems": ["FortiGate-Primary"],
        "recommended_diagnostics": ["diagnose user ban status"],
        "immediate_actions": ["Ban IP 1.2.3.4"],
    }
    monkeypatch.setattr(srv.security_review_service.ai_analyzer, "get_analysis", lambda aid: sample_analysis if aid == "an-api-test-01" else None)

    # Test HTML export (default)
    handler_html = DummyHandler()
    handler_html._handle_security_agent_analysis_report_get("an-api-test-01", {"format": ["html"]})
    assert handler_html.sent_status == 200
    assert "text/html" in handler_html.sent_headers["Content-Type"]
    assert b"an-api-test-01" in handler_html.response_body
    assert b"Active brute force observed" in handler_html.response_body

    # Test PDF export
    handler_pdf = DummyHandler()
    handler_pdf._handle_security_agent_analysis_report_get("an-api-test-01", {"format": ["pdf"]})
    assert handler_pdf.sent_status == 200
    assert "application/pdf" in handler_pdf.sent_headers["Content-Type"]
    assert handler_pdf.response_body.startswith(b"%PDF")

    # Test JSON export
    handler_json = DummyHandler()
    handler_json._handle_security_agent_analysis_report_get("an-api-test-01", {"format": ["json"]})
    assert handler_json.sent_status == 200
    assert "application/json" in handler_json.sent_headers["Content-Type"]
    data = json.loads(handler_json.response_body.decode("utf-8"))
    assert data["analysis_id"] == "an-api-test-01"

