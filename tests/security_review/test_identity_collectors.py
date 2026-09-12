import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import json
import pytest
from core.connectors.security.ad_exchange_collector import ActiveDirectoryCollector, ExchangeCollector
from core.connectors.security.models import (
    CollectorRequest,
    CollectorStatus,
    ThreatCategory,
)
from core.security_review.contracts import (
    DiagnosticStage,
    DiagnosticStatus,
)


def test_ad_privileged_group_change_parsing():
    sample_event = {
        "EventID": 4728,
        "TargetUserName": "Domain Admins",
        "MemberName": "CN=TemporaryUser,OU=Users,DC=mne,DC=gov,DC=ps",
        "SubjectUserName": "svc_installer",
        "TimeCreated": "2026-09-06T05:22:00Z",
    }
    collector = ActiveDirectoryCollector()
    event = collector.parse_security_event(sample_event)
    assert event.source_device == "Active Directory"
    assert event.category == ThreatCategory.PRIVILEGE_CHANGE
    assert "Member added to Domain Admins" in event.threat_name
    assert event.target == "TemporaryUser"
    assert event.timestamp == datetime(2026, 9, 6, 5, 22, 0, tzinfo=timezone.utc)


def test_ad_account_lockout_parsing():
    sample_event = {
        "EventID": 4740,
        "TargetUserName": "finance_mgr",
        "CallerComputerName": "WORKSTATION-102",
        "TimeCreated": "2026-09-06T04:15:00Z",
    }
    collector = ActiveDirectoryCollector()
    event = collector.parse_security_event(sample_event)
    assert event.source_device == "Active Directory"
    assert event.category == ThreatCategory.BRUTE_FORCE
    assert "Account Locked Out" in event.threat_name
    assert event.target == "finance_mgr"
    assert event.timestamp == datetime(2026, 9, 6, 4, 15, 0, tzinfo=timezone.utc)


def test_ad_expanded_identity_events_and_xml_fields():
    collector = ActiveDirectoryCollector()

    # Event 4720: User account created
    evt_4720 = {
        "EventID": 4720,
        "TargetUserName": "new_emp_01",
        "TargetSid": "S-1-5-21-12345678-500",
        "WorkstationName": "DC-PRIMARY",
        "TimeCreated": "2026-09-06T08:00:00Z",
    }
    parsed_4720 = collector.parse_security_event(evt_4720)
    assert parsed_4720.category == ThreatCategory.PRIVILEGE_CHANGE
    assert "User Account Created: new_emp_01" in parsed_4720.threat_name
    assert parsed_4720.metadata["TargetSid"] == "S-1-5-21-12345678-500"

    # Event 4768: Kerberos Pre-Auth Failure
    evt_4768 = {
        "EventID": 4768,
        "TargetUserName": "admin_svc",
        "Status": "0x18",
        "FailureCode": "0x18",
        "TimeCreated": "2026-09-06T09:30:00Z",
    }
    parsed_4768 = collector.parse_security_event(evt_4768)
    assert parsed_4768.category == ThreatCategory.BRUTE_FORCE
    assert parsed_4768.action_taken == "DROPPED"
    assert "Kerberos Pre-Auth Failure" in parsed_4768.threat_name
    assert parsed_4768.metadata["Status"] == "0x18"


def test_ad_winrm_query_time_range_and_pagination(monkeypatch):
    monkeypatch.setenv("MNE_AD_CREDENTIAL_REF", "fixture-auth-token")
    auth_credential = os.environ["MNE_AD_CREDENTIAL_REF"]
    collector = ActiveDirectoryCollector(host="172.23.71.27", password=auth_credential)
    req = CollectorRequest(
        start_time="2026-09-06T00:00:00Z",
        end_time="2026-09-06T23:59:59Z",
        max_records=2,
    )

    fake_ad_events = [
        {"EventID": 4740, "TargetUserName": "user1", "TimeCreated": "2026-09-06T04:00:00Z"},
        {"EventID": 4625, "TargetUserName": "user2", "TimeCreated": "2026-09-06T05:00:00Z"},
        {"EventID": 4728, "TargetUserName": "Admins", "MemberName": "CN=user3", "TimeCreated": "2026-09-06T06:00:00Z"},
    ]

    mock_session = MagicMock()
    mock_res = MagicMock()
    mock_res.status_code = 0
    mock_res.std_out = json.dumps(fake_ad_events).encode("utf-8")
    mock_res.std_err = b""
    mock_session.run_ps.return_value = mock_res

    with patch("winrm.Session", return_value=mock_session):
        result = collector.collect_logs(request=req)
        assert result.status == CollectorStatus.SUCCESS
        assert len(result.events) == 2
        assert result.diagnostic.pagination["has_more"] is True

        # Check script content contained StartTime and EndTime
        ps_sent = mock_session.run_ps.call_args[0][0]
        assert "StartTime" in ps_sent
        assert "EndTime" in ps_sent
        assert "2026-09-06" in ps_sent


def test_ad_powershell_error_produces_failure_diagnostic(monkeypatch):
    monkeypatch.setenv("MNE_AD_CREDENTIAL_REF", "fixture-auth-token")
    auth_credential = os.environ["MNE_AD_CREDENTIAL_REF"]
    collector = ActiveDirectoryCollector(host="172.23.71.27", password=auth_credential)
    req = CollectorRequest(hours_back=24)

    mock_session = MagicMock()
    mock_res = MagicMock()
    mock_res.status_code = 1
    mock_res.std_out = b""
    mock_res.std_err = b"Get-WinEvent : The RPC server is unavailable."
    mock_session.run_ps.return_value = mock_res

    with patch("winrm.Session", return_value=mock_session):
        result = collector.collect_logs(request=req)
        # Errors must NOT be swallowed or returned as zero-event success
        assert result.status == CollectorStatus.FAILED
        assert "RPC server is unavailable" in result.error_message
        assert result.diagnostic.status == DiagnosticStatus.FAILED
        assert result.diagnostic.stage == DiagnosticStage.QUERY


def test_exchange_relay_anomaly_parsing():
    sample_log = {
        "event_type": "FAIL",
        "client_ip": "185.190.140.22",
        "sender": "spammer@external-junk.com",
        "recipient_count": 140,
        "reason": "550 5.7.1 Unable to relay",
        "timestamp": "2026-09-06T03:30:00Z",
    }
    collector = ExchangeCollector()
    event = collector.parse_tracking_log(sample_log)
    assert event.source_device == "Exchange"
    assert event.category == ThreatCategory.ANOMALY
    assert event.attacker_ip == "185.190.140.22"
    assert "Relay Attempt Blocked" in event.threat_name
    assert event.action_taken == "BLOCKED"
    assert event.timestamp == datetime(2026, 9, 6, 3, 30, 0, tzinfo=timezone.utc)


def test_exchange_separate_security_and_tracking_parsing():
    collector = ExchangeCollector()

    # Windows Security / OWA auth failure
    sec_event = {
        "EventID": 4625,
        "TargetUserName": "finance_head",
        "IpAddress": "194.26.29.112",
        "TimeCreated": "2026-09-06T02:00:00Z",
    }
    parsed_sec = collector.parse_security_event(sec_event)
    assert parsed_sec.source_device == "Exchange"
    assert parsed_sec.category == ThreatCategory.BRUTE_FORCE
    assert parsed_sec.action_taken == "DROPPED"
    assert "OWA/Logon Failure: finance_head" in parsed_sec.threat_name
    assert parsed_sec.timestamp == datetime(2026, 9, 6, 2, 0, 0, tzinfo=timezone.utc)
