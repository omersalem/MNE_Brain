import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from core.connectors.security.fortiedr_collector import (
    FortiEDRSecurityCollector,
    _parse_dwr_reply,
    _tokenify,
)
from core.connectors.security.models import (
    CollectorRequest,
    CollectorStatus,
    ThreatCategory,
)
from core.security_review.config import SecurityAgentConfig
from core.security_review.contracts import (
    DiagnosticStage,
    DiagnosticStatus,
    SecurityReviewRequest,
)
from core.security_review.service import (
    CANONICAL_COLLECTOR_MAP,
    _default_collector_factory,
)


def test_fortiedr_tokenify():
    token = _tokenify(123456789.0)
    assert isinstance(token, str)
    assert len(token) > 0
    assert _tokenify(0) == "0"


def test_parse_dwr_reply_quoted_json():
    sample = '//#DWR-REPLY\ndwr.engine._remoteHandleCallback("0", "0", "{\\"id\\": 11394210, \\"name\\": \\"MNE\\"}");\n})();'
    result = _parse_dwr_reply(sample)
    assert isinstance(result, dict)
    assert result.get("id") == 11394210
    assert result.get("name") == "MNE"


def test_parse_dwr_reply_raw_json():
    sample = '//#DWR-REPLY\ndwr.engine._remoteHandleCallback("0", "0", [{"name": "Enabled", "Enabled": 64}]);\n})();'
    result = _parse_dwr_reply(sample)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["name"] == "Enabled"


def test_parse_dwr_reply_exception():
    sample = '//#DWR-REPLY\ndwr.engine._remoteHandleException({message: "Session expired", code: 401});'
    result = _parse_dwr_reply(sample)
    assert isinstance(result, dict)
    assert "error" in result


def test_parse_dwr_reply_fallback():
    sample = "plain string without callback"
    result = _parse_dwr_reply(sample)
    assert result == sample


FIXTURE_CREDENTIAL = "fixture-" + "credential"


def test_fortiedr_parse_security_event_malicious():
    collector = FortiEDRSecurityCollector(
        host="test.console.ensilo.com",
        username="testuser",
        password=FIXTURE_CREDENTIAL,
        organization="MNE",
    )
    raw_event = {
        "id": "1001",
        "classification": "Malicious",
        "organization": "MNE",
        "lastSeen": "12-Sep-2026, 10:15:30",
        "ip": "172.23.71.100",
        "device": "MNE-WS-FINANCE-01",
    }
    norm = collector.parse_security_event(raw_event)
    assert norm.source_device == "FortiEDR"
    assert norm.event_id == "edr-1001"
    assert norm.category == ThreatCategory.MALWARE
    assert norm.action_taken == "BLOCKED"
    assert norm.attacker_ip == "172.23.71.100"
    assert norm.target == "MNE-WS-FINANCE-01"
    assert "Malicious" in norm.threat_name
    assert norm.metadata["canonical_entity"] == "edr-fortiedr-cloud-01"
    assert norm.metadata["collector_id"] == "fortiedr"
    assert norm.timestamp == datetime(2026, 9, 12, 7, 15, 30, tzinfo=timezone.utc)
    assert norm.metadata["source_timezone"] == "Africa/Cairo"


def test_fortiedr_parse_security_event_suspicious():
    collector = FortiEDRSecurityCollector(
        host="test.console.ensilo.com",
        username="testuser",
        password=FIXTURE_CREDENTIAL,
        organization="MNE",
    )
    raw_event = {
        "id": "1002",
        "classification": "Suspicious",
        "organization": "MNE",
        "lastSeen": "12-Sep-2026 10:20:00",
        "ip": "172.23.71.105",
        "device": "MNE-SRV-APP",
    }
    norm = collector.parse_security_event(raw_event)
    assert norm.category == ThreatCategory.INTRUSION
    assert norm.action_taken == "ALERT"


def test_fortiedr_parse_security_event_inconclusive():
    collector = FortiEDRSecurityCollector(
        host="test.console.ensilo.com",
        username="testuser",
        password=FIXTURE_CREDENTIAL,
        organization="MNE",
    )
    raw_event = {
        "id": "1003",
        "classification": "Inconclusive",
        "organization": "MNE",
    }
    norm = collector.parse_security_event(raw_event)
    assert norm.category == ThreatCategory.ANOMALY
    assert norm.action_taken == "ALERT"


def test_fortiedr_safe_event_is_not_malware():
    collector = FortiEDRSecurityCollector(
        host="test.console.ensilo.com",
        username="testuser",
        password=FIXTURE_CREDENTIAL,
        organization="MNE",
    )
    norm = collector.parse_security_event({"id": "1004", "classification": "Safe"})
    assert norm.category == ThreatCategory.ANOMALY
    assert norm.action_taken == "ALLOWED"


def test_fortiedr_missing_password_error():
    with patch.dict(os.environ, {"MNE_FORTIEDR_PASSWORD": ""}):
        collector = FortiEDRSecurityCollector(password="")
        result = collector.collect_logs(CollectorRequest(hours_back=1))
        assert result.status == CollectorStatus.FAILED
        assert "MNE_FORTIEDR_PASSWORD is not configured" in str(result.error_message)


def test_fortiedr_mock_collection_flow():
    collector = FortiEDRSecurityCollector(
        host="mock.console.ensilo.com",
        username="mockuser",
        password=FIXTURE_CREDENTIAL,
        organization="MNE",
    )

    with patch("requests.Session") as mock_session_cls:
        session = MagicMock()
        mock_session_cls.return_value = session

        # 1. Login response
        login_resp = MagicMock()
        login_resp.status_code = 302
        login_resp.headers = {"Set-Cookie": "JSESSIONID=MOCK_SESS_12345; Path=/"}
        session.cookies.get.side_effect = lambda k, default=None: "MOCK_SESS_12345" if k == "JSESSIONID" else default

        # 2. DWR responses
        dwr_acct_resp = MagicMock()
        dwr_acct_resp.status_code = 200
        dwr_acct_resp.text = 'handleCallback("0", "0", "{\\"id\\": 11394210, \\"name\\": \\"MNE\\"}");\n})();'

        dwr_events_resp = MagicMock()
        dwr_events_resp.status_code = 200
        current_source_time = datetime.now(timezone.utc).astimezone(ZoneInfo("Africa/Cairo"))
        dwr_events_resp.text = json.dumps({
            "newEvents": [
                {
                    "id": "9001",
                    "classification": "Malicious",
                    "organization": "MNE",
                        "lastSeen": current_source_time.strftime("%d-%b-%Y, %H:%M:%S"),
                    "ip": "172.23.70.50",
                    "device": "FINANCE-PC",
                }
            ],
            "newEventsCount": 1,
        })
        dwr_events_wrapper = MagicMock()
        dwr_events_wrapper.status_code = 200
        dwr_events_wrapper.text = f'handleCallback("0", "0", {dwr_events_resp.text});\n}})();'

        dwr_health_resp = MagicMock()
        dwr_health_resp.status_code = 200
        dwr_health_resp.text = 'handleCallback("0", "0", [{"name": "Enabled", "Enabled": 10}, {"name": "Degraded", "Degraded": 2}]);\n})();'

        dwr_infra_resp = MagicMock()
        dwr_infra_resp.status_code = 200
        dwr_infra_resp.text = 'handleCallback("0", "0", [{"name": "Cores", "Cores": 1}, {"name": "Aggregators", "Aggregators": 2}]);\n})();'

        dwr_apps_resp = MagicMock()
        dwr_apps_resp.status_code = 200
        dwr_apps_resp.text = 'handleCallback("0", "0", [{"name": "Critical CVEs", "Critical CVEs": 5}]);\n})();'

        session.post.side_effect = [
            login_resp,
            dwr_acct_resp,
            dwr_events_wrapper,
            dwr_health_resp,
            dwr_infra_resp,
            dwr_apps_resp,
        ]

        result = collector.collect_logs(CollectorRequest(hours_back=24, max_records=10))

        assert result.status == CollectorStatus.SUCCESS
        assert len(result.events) >= 2  # Threat event + health / apps
        assert result.diagnostic.stage == DiagnosticStage.COMPLETE
        assert result.diagnostic.status == DiagnosticStatus.SUCCESS
        assert result.diagnostic.canonical_entity == "edr-fortiedr-cloud-01"


def test_fortiedr_auth_failure_handling():
    collector = FortiEDRSecurityCollector(
        host="mock.console.ensilo.com",
        username="baduser",
        password=FIXTURE_CREDENTIAL,
        organization="MNE",
    )
    with patch("requests.Session") as mock_session_cls:
        session = MagicMock()
        mock_session_cls.return_value = session

        login_resp = MagicMock()
        login_resp.status_code = 401
        session.post.return_value = login_resp

        result = collector.collect_logs(CollectorRequest(hours_back=1))
        assert result.status == CollectorStatus.FAILED
        assert result.diagnostic.stage == DiagnosticStage.AUTHENTICATION
        assert result.diagnostic.status == DiagnosticStatus.FAILED
        assert result.diagnostic.diagnostic_code == "AUTH_FAILED"


def test_fortiedr_pipeline_registration():
    # 1. Base map
    assert CANONICAL_COLLECTOR_MAP.get("fortiedr") == "FortiEDR"

    # 2. Factory
    collector = _default_collector_factory("fortiedr")
    assert isinstance(collector, FortiEDRSecurityCollector)
    assert collector.device_name == "FortiEDR"

    # 3. SecurityReviewRequest defaults
    req = SecurityReviewRequest()
    assert "fortiedr" in req.collector_ids

    # 4. Device catalog
    catalog = SecurityAgentConfig().get_device_catalog()
    ids = [d["id"] for d in catalog]
    assert "fortiedr" in ids
    fortiedr_entry = next(d for d in catalog if d["id"] == "fortiedr")
    assert fortiedr_entry["name"] == "FortiEDR Cloud Central Manager"
    assert fortiedr_entry["ip"] == "fortiedrconnectil.console.ensilo.com"
    assert fortiedr_entry["protocol"] == "HTTPS Console API / DWR"


@pytest.mark.skipif(
    os.getenv("MNE_RUN_LIVE_SECURITY_TESTS") != "1" or not os.getenv("MNE_FORTIEDR_PASSWORD"),
    reason="Live security tests require MNE_RUN_LIVE_SECURITY_TESTS=1 and configured credentials",
)
def test_fortiedr_live_collection():
    collector = FortiEDRSecurityCollector()
    result = collector.collect_logs(CollectorRequest(hours_back=24, max_records=5))
    assert result.status == CollectorStatus.SUCCESS
    assert result.diagnostic.stage == DiagnosticStage.COMPLETE
    assert result.diagnostic.status == DiagnosticStatus.SUCCESS
    assert result.diagnostic.canonical_entity == "edr-fortiedr-cloud-01"
    assert len(result.events) > 0
