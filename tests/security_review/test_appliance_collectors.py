import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from core.connectors.security.fmc_collector import FmcSecurityCollector
from core.connectors.security.sophos_collector import SophosEmailCollector
from core.connectors.security.models import (
    CollectorRequest,
    CollectorStatus,
    ThreatCategory,
)
from core.security_review.contracts import (
    DiagnosticStage,
    DiagnosticStatus,
)


def test_fmc_intrusion_parsing():
    sample_fmc_item = {
        "id": "fmc-event-101",
        "timestamp": 1788680000,
        "sourceIp": "45.155.205.233",
        "destinationIp": "172.23.200.2",
        "ruleMessage": "SERVER-WEBAPP Apache Log4j remote code execution attempt",
        "classification": "Attempted Administrator Privilege Gain",
        "impact": "Red",
        "action": "Block",
    }
    collector = FmcSecurityCollector()
    event = collector.parse_fmc_event(sample_fmc_item)
    assert event.source_device == "Cisco FMC"
    assert event.category == ThreatCategory.INTRUSION
    assert event.attacker_ip == "45.155.205.233"
    assert event.action_taken == "BLOCKED"
    assert "Log4j" in event.threat_name
    # Source timestamp preserved from epoch
    assert event.timestamp == datetime.fromtimestamp(1788680000, tz=timezone.utc)
    assert event.metadata.get("impact") == "Red"
    assert event.metadata.get("classification") == "Attempted Administrator Privilege Gain"


def test_fmc_security_intelligence_parsing():
    sample_si_item = {
        "id": "fmc-si-202",
        "timestamp": 1788681000,
        "sourceIp": "194.26.29.112",
        "destinationIp": "172.23.70.254",
        "ruleMessage": "Security Intelligence Block: Known Command and Control (C2) Server",
        "action": "Drop",
    }
    collector = FmcSecurityCollector()
    event = collector.parse_fmc_event(sample_si_item)
    assert event.source_device == "Cisco FMC"
    assert event.category == ThreatCategory.INTRUSION
    assert event.attacker_ip == "194.26.29.112"
    assert event.action_taken == "BLOCKED"


def test_fmc_fully_qualified_intrusion_event_parsing():
    sample_fqe_item = {
        "IntrusionEvent": {
            "EventID": "fqe-101",
            "EventSecond": 1788680000,
            "InitiatorIP": "45.155.205.233",
            "ResponderIP": "172.23.200.2",
            "IntrusionRuleMessage": "SERVER-WEBAPP Apache exploit attempt",
            "Classification": "Attempted Administrator Privilege Gain",
            "Impact": "Impact 1",
            "InlineResult": "Dropped",
            "Device": "FTD-Main",
        }
    }

    event = FmcSecurityCollector().parse_fmc_event(sample_fqe_item)

    assert event.event_id == "fmc-fqe-101"
    assert event.timestamp == datetime.fromtimestamp(1788680000, tz=timezone.utc)
    assert event.attacker_ip == "45.155.205.233"
    assert event.target == "172.23.200.2"
    assert event.threat_name == "SERVER-WEBAPP Apache exploit attempt"
    assert event.action_taken == "BLOCKED"
    assert event.metadata["classification"] == "Attempted Administrator Privilege Gain"
    assert event.metadata["impact"] == "Impact 1"
    assert event.metadata["managed_device"] == "FTD-Main"
    assert event.metadata["estreamer_event_type"] == "IntrusionEvent"


def test_fmc_domain_discovery_and_pagination(monkeypatch):
    monkeypatch.setenv("MNE_FMC_CREDENTIAL_REF", "fixture-auth-token")
    auth_credential = os.environ["MNE_FMC_CREDENTIAL_REF"]
    collector = FmcSecurityCollector(host="172.23.70.77", password=auth_credential)
    req = CollectorRequest(
        start_time="2026-09-01T00:00:00Z",
        end_time="2026-09-10T00:00:00Z",
        max_records=2,
    )

    auth_resp = MagicMock()
    auth_resp.status_code = 200
    auth_resp.headers = {"X-auth-access-token": "test-fmc-tok", "DOMAIN_UUID": "domain-uuid-xyz"}

    q_resp = MagicMock()
    q_resp.status_code = 200
    q_resp.json.return_value = {
        "items": [
            {"id": "ev1", "timestamp": 1788680000, "ruleMessage": "Intrusion 1", "sourceIp": "1.1.1.1", "action": "block"},
            {"id": "ev2", "timestamp": 1788680100, "ruleMessage": "Intrusion 2", "sourceIp": "1.1.1.2", "action": "block"},
            {"id": "ev3", "timestamp": 1788680200, "ruleMessage": "Intrusion 3", "sourceIp": "1.1.1.3", "action": "block"},
        ]
    }

    with patch("requests.post", return_value=auth_resp), patch("requests.get", return_value=q_resp):
        result = collector.collect_logs(request=req)
        assert result.status == CollectorStatus.WARNING
        assert len(result.events) == 2
        assert result.diagnostic.pagination["has_more"] is True
        assert result.diagnostic.diagnostic_code == "TRUNCATED_AT_LIMIT"
        assert "domain-uuid-xyz" in result.diagnostic.source_queried


def test_fmc_partial_diagnostics_on_rejected_endpoint(monkeypatch):
    monkeypatch.setenv("MNE_FMC_CREDENTIAL_REF", "fixture-auth-token")
    auth_credential = os.environ["MNE_FMC_CREDENTIAL_REF"]
    collector = FmcSecurityCollector(host="172.23.70.77", password=auth_credential, domain_uuid="domain-uuid-xyz")
    req = CollectorRequest(
        start_time="2026-09-01T00:00:00Z",
        end_time="2026-09-10T00:00:00Z",
        max_records=5,
    )

    auth_resp = MagicMock()
    auth_resp.status_code = 200
    auth_resp.headers = {"X-auth-access-token": "test-fmc-tok"}

    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.json.return_value = {
        "items": [
            {"id": "ev1", "timestamp": 1788680000, "ruleMessage": "Intrusion 1", "sourceIp": "1.1.1.1", "action": "block"},
        ]
    }

    fail_resp = MagicMock()
    fail_resp.status_code = 403

    def get_side_effect(url, **kwargs):
        if "securityintelligenceevents" in url:
            return fail_resp
        return ok_resp

    with patch("requests.post", return_value=auth_resp), patch("requests.get", side_effect=get_side_effect):
        result = collector.collect_logs(request=req)
        assert result.status == CollectorStatus.WARNING
        assert result.diagnostic.status == DiagnosticStatus.PARTIAL
        assert len(result.events) >= 1
        assert result.diagnostic.diagnostic_code == "PARTIAL_SUCCESS"
        assert "securityintelligenceevents" in result.diagnostic.message


def test_fmc_partial_status_when_threat_stream_unsupported_404(monkeypatch):
    monkeypatch.setenv("MNE_FMC_CREDENTIAL_REF", "fixture-auth-token")
    monkeypatch.setenv("MNE_FMC_ESTREAMER_JSONL_PATH", "")
    monkeypatch.setenv("MNE_FMC_ESTREAMER_HEALTH_PATH", "")
    auth_credential = os.environ["MNE_FMC_CREDENTIAL_REF"]
    collector = FmcSecurityCollector(host="172.23.70.77", password=auth_credential, domain_uuid="domain-uuid-xyz")
    req = CollectorRequest(
        start_time="2026-09-01T00:00:00Z",
        end_time="2026-09-10T00:00:00Z",
        max_records=5,
    )

    auth_resp = MagicMock()
    auth_resp.status_code = 200
    auth_resp.headers = {"X-auth-access-token": "test-fmc-tok"}

    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.json.return_value = {
        "items": [
            {"id": "ev1", "timestamp": 1788680000, "ruleMessage": "Audit Login Success", "sourceIp": "1.1.1.1", "action": "allow"},
        ]
    }

    fail_resp = MagicMock()
    fail_resp.status_code = 404

    def get_side_effect(url, **kwargs):
        if "intrusionevents" in url or "securityintelligenceevents" in url:
            return fail_resp
        return ok_resp

    with patch("requests.post", return_value=auth_resp), patch("requests.get", side_effect=get_side_effect):
        result = collector.collect_logs(request=req)
        assert result.status == CollectorStatus.WARNING
        assert result.diagnostic.status == DiagnosticStatus.PARTIAL
        assert len(result.events) >= 1
        assert result.diagnostic.diagnostic_code == "THREAT_STREAMS_UNAVAILABLE"
        assert result.diagnostic.pagination["threat_stream_available"] is False


def test_fmc_estreamer_spool_restores_threat_stream_coverage(monkeypatch, tmp_path):
    monkeypatch.setenv("MNE_FMC_CREDENTIAL_REF", "fixture-auth-token")
    spool = tmp_path / "fmc-estreamer.jsonl"
    spool.write_text(
        '{"id":"stream-1","timestamp":1788680000,"sourceIp":"1.1.1.1",'
        '"destinationIp":"2.2.2.2","ruleMessage":"Intrusion event","action":"block"}\n',
        encoding="utf-8",
    )
    collector = FmcSecurityCollector(
        host="172.23.70.77",
        password=os.environ["MNE_FMC_CREDENTIAL_REF"],
        domain_uuid="domain-uuid-xyz",
        estreamer_jsonl_path=str(spool),
    )
    req = CollectorRequest(
        start_time="2026-09-01T00:00:00Z",
        end_time="2026-09-10T00:00:00Z",
        max_records=5,
    )
    auth_resp = MagicMock(status_code=200, headers={"X-auth-access-token": "test-fmc-tok"})
    unsupported = MagicMock(status_code=404)
    audit = MagicMock(status_code=200)
    audit.json.return_value = {"items": []}

    def get_side_effect(url, **kwargs):
        return unsupported if "intrusionevents" in url or "securityintelligenceevents" in url else audit

    with patch("requests.post", return_value=auth_resp), patch("requests.get", side_effect=get_side_effect):
        result = collector.collect_logs(request=req)

    assert result.status == CollectorStatus.SUCCESS
    assert len(result.events) == 1
    assert result.events[0].metadata["transport"] == "ESTREAMER_JSONL_SPOOL"
    assert result.diagnostic.pagination["threat_stream_available"] is True


def test_fmc_empty_estreamer_spool_is_not_healthy_threat_stream(monkeypatch, tmp_path):
    monkeypatch.setenv("MNE_FMC_CREDENTIAL_REF", "fixture-auth-token")
    spool = tmp_path / "fmc-estreamer.jsonl"
    spool.write_text("", encoding="utf-8")
    collector = FmcSecurityCollector(
        host="172.23.70.77",
        password=os.environ["MNE_FMC_CREDENTIAL_REF"],
        domain_uuid="domain-uuid-xyz",
        estreamer_jsonl_path=str(spool),
    )
    req = CollectorRequest(
        start_time="2026-09-01T00:00:00Z",
        end_time="2026-09-10T00:00:00Z",
        max_records=5,
    )
    auth_resp = MagicMock(status_code=200, headers={"X-auth-access-token": "test-fmc-tok"})
    unsupported = MagicMock(status_code=404)
    audit = MagicMock(status_code=200)
    audit.json.return_value = {"items": []}

    def get_side_effect(url, **kwargs):
        return unsupported if "intrusionevents" in url or "securityintelligenceevents" in url else audit

    with patch("requests.post", return_value=auth_resp), patch("requests.get", side_effect=get_side_effect):
        result = collector.collect_logs(request=req)

    assert result.status == CollectorStatus.WARNING
    assert result.diagnostic.diagnostic_code == "THREAT_STREAMS_UNAVAILABLE"
    assert result.diagnostic.pagination["endpoint_diagnostics"]["estreamer"]["status"] == "EMPTY"
    assert result.diagnostic.pagination["threat_stream_available"] is False


def test_fmc_rotated_estreamer_spool_files_are_loaded(monkeypatch, tmp_path):
    monkeypatch.setenv("MNE_FMC_CREDENTIAL_REF", "fixture-auth-token")
    active = tmp_path / "events.jsonl"
    archive = tmp_path / "events-20260912T070000000Z.jsonl"
    record_template = (
        '{{"id":"{event_id}","timestamp":1788680000,"sourceIp":"1.1.1.1",'
        '"destinationIp":"2.2.2.2","ruleMessage":"Intrusion event","action":"block"}}\n'
    )
    archive.write_text(record_template.format(event_id="stream-archive"), encoding="utf-8")
    active.write_text(record_template.format(event_id="stream-active"), encoding="utf-8")
    collector = FmcSecurityCollector(
        host="172.23.70.77",
        password=os.environ["MNE_FMC_CREDENTIAL_REF"],
        domain_uuid="domain-uuid-xyz",
        estreamer_jsonl_path=str(active),
    )
    req = CollectorRequest(
        start_time="2026-09-01T00:00:00Z",
        end_time="2026-09-10T00:00:00Z",
        max_records=5,
    )
    auth_resp = MagicMock(status_code=200, headers={"X-auth-access-token": "test-fmc-tok"})
    unsupported = MagicMock(status_code=404)
    audit = MagicMock(status_code=200)
    audit.json.return_value = {"items": []}

    def get_side_effect(url, **kwargs):
        return unsupported if "intrusionevents" in url or "securityintelligenceevents" in url else audit

    with patch("requests.post", return_value=auth_resp), patch("requests.get", side_effect=get_side_effect):
        result = collector.collect_logs(request=req)

    assert result.status == CollectorStatus.SUCCESS
    assert {event.event_id for event in result.events} == {"fmc-stream-archive", "fmc-stream-active"}
    assert result.diagnostic.pagination["endpoint_diagnostics"]["estreamer"]["records_fetched"] == 2


def test_fmc_successful_api_audit_is_operational_telemetry():
    event = FmcSecurityCollector().parse_fmc_event({
        "auditId": "audit-1",
        "subSystem": "API",
        "message": "GET https://localhost/api/local/fmc_platform/v1/info/domain OK (200) - The request has succeeded",
        "timestamp": 1788680000,
    })
    assert event.category == ThreatCategory.SYSTEM_HEALTH
    assert event.action_taken == "ALLOWED"
    assert event.threat_name.startswith("FMC Audit:")


def test_sophos_email_quarantine_parsing():
    sample_quarantine_entry = {
        "mail_id": "sp-998811",
        "sender": "attacker@compromised-gov.com",
        "recipient": "minister-office@mne.gov.ps",
        "reason": "Malware detected: Trojan.VBS.Agent",
        "sandbox_verdict": "Malicious",
        "action": "Quarantined",
        "timestamp": "2026-09-06T02:45:00Z",
        "subject": "Urgent Invoice Document",
    }
    collector = SophosEmailCollector()
    event = collector.parse_quarantine_entry(sample_quarantine_entry)
    assert event.source_device == "Sophos Email"
    assert event.category == ThreatCategory.MALWARE
    assert event.target == "minister-office@mne.gov.ps"
    assert event.action_taken == "QUARANTINED"
    assert "Trojan" in event.threat_name
    # Source timestamp preserved
    assert event.timestamp == datetime(2026, 9, 6, 2, 45, 0, tzinfo=timezone.utc)
    assert "subject_hash" in event.metadata


def test_sophos_spam_burst_parsing():
    sample_entry = {
        "mail_id": "sp-112233",
        "sender": "spammer@bulk-mailer.biz",
        "recipient": "all-staff@mne.gov.ps",
        "reason": "High confidence Spam surge",
        "action": "Dropped",
        "timestamp": "2026-09-06T03:00:00Z",
    }
    collector = SophosEmailCollector()
    event = collector.parse_quarantine_entry(sample_entry)
    assert event.source_device == "Sophos Email"
    assert event.category == ThreatCategory.PHISHING
    assert event.action_taken == "DROPPED"


def test_sophos_dkim_spf_reject_parsing():
    collector = SophosEmailCollector()
    log_line = (
        "2026-09-06 08:29:08.746Z [13449] H=mail.spoof.net [185.190.140.22]:59371 "
        "F=<spoofed@trusted-partner.com> rejected RCPT <admin@mne.gov.ps>: SPF check failed: domain does not permit sender"
    )
    event = collector.parse_reject_log_line(log_line)
    assert event is not None
    assert event.category == ThreatCategory.PHISHING
    assert event.action_taken == "DROPPED"
    assert event.attacker_ip == "185.190.140.22"
    assert event.target == "admin@mne.gov.ps"
    assert event.timestamp == datetime(2026, 9, 6, 8, 29, 8, 746000, tzinfo=timezone.utc)


def test_sophos_quarantine_log_line_parsing():
    collector = SophosEmailCollector()
    log_line = (
        '2026-09-06 02:45:00.000Z [quarantine] mail_id="sp-998811" '
        'sender="attacker@bad.com" recipient="victim@mne.gov.ps" '
        'reason="Malware detected: Trojan.VBS.Agent" action="Quarantined" client_ip="198.51.100.22"'
    )
    event = collector.parse_quarantine_log_line(log_line)
    assert event is not None
    assert event.source_device == "Sophos Email"
    assert event.category == ThreatCategory.MALWARE
    assert event.action_taken == "QUARANTINED"
    assert event.target == "victim@mne.gov.ps"
    assert event.attacker_ip == "198.51.100.22"
    assert "Trojan" in event.threat_name


def test_sophos_malware_log_line_parsing():
    collector = SophosEmailCollector()
    log_line = (
        '2026-09-06 03:12:00.000Z [av] infected with Trojan.Agent.Generic '
        'file="payload.exe" sender="spammer@threat.org" recipient="staff@mne.gov.ps" src="198.51.100.33"'
    )
    event = collector.parse_malware_log_line(log_line)
    assert event is not None
    assert event.category == ThreatCategory.MALWARE
    assert event.action_taken == "DROPPED"
    assert "Trojan.Agent.Generic" in event.threat_name
    assert event.metadata["filename"] == "payload.exe"


def test_sophos_auth_log_line_parsing():
    collector = SophosEmailCollector()
    log_line = '2026-09-06 04:00:15.000Z [auth] user "admin" authentication failed from "185.220.101.5"'
    event = collector.parse_auth_log_line(log_line)
    assert event is not None
    assert event.category == ThreatCategory.BRUTE_FORCE
    assert event.attacker_ip == "185.220.101.5"
    assert event.target == "admin"
    assert event.action_taken == "DROPPED"


def test_sophos_delivery_log_line_parsing():
    collector = SophosEmailCollector()
    log_line = (
        '2026-09-06 05:20:00.000Z [delivery] TLS negotiation failed with 198.51.100.80: '
        'certificate expired recipient="finance@mne.gov.ps"'
    )
    event = collector.parse_delivery_log_line(log_line)
    assert event is not None
    assert event.category == ThreatCategory.SYSTEM_HEALTH
    assert event.action_taken == "ALERT"
    assert "TLS" in event.threat_name
    assert event.target == "finance@mne.gov.ps"
