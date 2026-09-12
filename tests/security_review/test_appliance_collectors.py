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
        assert result.status == CollectorStatus.SUCCESS
        assert len(result.events) == 2
        assert result.diagnostic.pagination["has_more"] is True
        assert result.diagnostic.diagnostic_code == "OK"
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


def test_fmc_complete_status_when_optional_stream_unsupported_404(monkeypatch):
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
        assert result.status == CollectorStatus.SUCCESS
        assert result.diagnostic.status == DiagnosticStatus.SUCCESS
        assert len(result.events) >= 1
        assert result.diagnostic.diagnostic_code == "OK"


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
