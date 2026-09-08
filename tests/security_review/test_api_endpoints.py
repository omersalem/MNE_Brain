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
