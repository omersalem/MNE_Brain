import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from core.connectors.security.fortigate_collector import FortiGateSecurityCollector
from core.connectors.security.f5_collector import F5SecurityCollector
from core.connectors.security.models import (
    CollectorRequest,
    CollectorStatus,
    ThreatCategory,
)


def test_fortigate_vpn_log_parsing():
    sample_log = (
        'date=2026-09-06 time=04:12:00 devname="FGT-Edge" logid="0101037128" '
        'type="event" subtype="vpn" level="alert" action="tunnel-down" '
        'remip="185.220.101.5" user="admin" reason="negotiation failure" '
        'msg="SSL VPN login fail"'
    )
    collector = FortiGateSecurityCollector()
    event = collector.parse_log_line(sample_log)
    assert event is not None
    assert event.source_device == "FortiGate"
    assert event.category == ThreatCategory.BRUTE_FORCE
    assert event.attacker_ip == "185.220.101.5"
    assert event.target == "admin"
    assert event.action_taken == "DROPPED"
    # Source timestamp preserved
    assert event.timestamp == datetime(2026, 9, 6, 4, 12, 0, tzinfo=timezone.utc)


def test_fortigate_ips_log_parsing():
    sample_log = (
        'date=2026-09-06 time=05:10:20 devname="FGT-Edge" logid="0419016384" '
        'type="ips" subtype="signature" level="critical" action="dropped" '
        'srcip=45.155.205.233 dstip=172.23.200.2 attack="Apache.Log4j.Error.Log.Remote.Code.Execution" '
        'msg="detected Log4j exploit attempt" policyid=42 vdom="root" srcintf="wan1" dstintf="internal"'
    )
    collector = FortiGateSecurityCollector()
    event = collector.parse_log_line(sample_log)
    assert event is not None
    assert event.source_device == "FortiGate"
    assert event.category == ThreatCategory.INTRUSION
    assert event.attacker_ip == "45.155.205.233"
    assert event.target == "172.23.200.2"
    assert event.action_taken == "DROPPED"
    assert "Log4j" in event.threat_name
    assert event.timestamp == datetime(2026, 9, 6, 5, 10, 20, tzinfo=timezone.utc)
    # Metadata fields
    assert event.metadata.get("policy_id") == "42"
    assert event.metadata.get("vdom") == "root"
    assert event.metadata.get("src_interface") == "wan1"
    assert event.metadata.get("dst_interface") == "internal"


def test_fortigate_rest_query_time_range_and_pagination(monkeypatch):
    monkeypatch.setenv("MNE_FORTIGATE_CREDENTIAL_REF", "fixture-auth-token")
    auth_credential = os.environ["MNE_FORTIGATE_CREDENTIAL_REF"]
    collector = FortiGateSecurityCollector(host="172.23.70.4", api_key=auth_credential)
    req = CollectorRequest(
        start_time="2026-09-06T00:00:00Z",
        end_time="2026-09-06T23:59:59Z",
        max_records=2,
    )

    fake_items = [
        {"date": "2026-09-06", "time": "08:00:00", "logid": "1", "type": "ips", "attack": "Att1", "srcip": "1.1.1.1", "dstip": "2.2.2.2", "action": "dropped"},
        {"date": "2026-09-06", "time": "09:00:00", "logid": "2", "type": "ips", "attack": "Att2", "srcip": "1.1.1.2", "dstip": "2.2.2.2", "action": "dropped"},
        {"date": "2026-09-06", "time": "10:00:00", "logid": "3", "type": "ips", "attack": "Att3", "srcip": "1.1.1.3", "dstip": "2.2.2.2", "action": "dropped"},
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"results": fake_items}

    with patch("requests.get", return_value=mock_resp) as mock_get:
        result = collector.collect_logs(request=req)
        assert mock_get.called
        # Verify requested time window appeared in query parameters
        call_params = mock_get.call_args[1].get("params", {})
        assert "start" in call_params
        assert "end" in call_params
        assert "2026-09-06" in call_params["start"]

        # Pagination stopped at max_records (2)
        assert len(result.events) == 2
        assert result.diagnostic.pagination["has_more"] is True
        assert result.diagnostic.records_parsed == 2


def test_f5_asm_log_parsing():
    sample_asm_line = (
        'Sep  6 03:15:22 f5-core.mne.gov.ps ASM: Attack detected: '
        'Support ID: 18273619283719, Client IP: 194.26.29.112, '
        'Violations: SQL-Injection, Severity: Critical, Action: Blocked, '
        'URL: /portal/login.aspx'
    )
    collector = F5SecurityCollector()
    event = collector.parse_asm_log_line(sample_asm_line)
    assert event is not None
    assert event.source_device == "F5 BIG-IP"
    assert event.category == ThreatCategory.WAF_EXPLOIT
    assert event.attacker_ip == "194.26.29.112"
    assert event.action_taken == "BLOCKED"
    assert "SQL-Injection" in event.threat_name
    # Source timestamp preserved
    year = datetime.now(timezone.utc).year
    assert event.timestamp.month == 9
    assert event.timestamp.day == 6
    assert event.timestamp.hour == 3
    assert event.timestamp.minute == 15


def test_f5_cert_warning_parsing():
    sample_log_line = (
        'Sep  6 02:00:10 f5-core warning mcpd[8123]: 0107143a:4: '
        'Certificate mne_wildcard_2026.crt in /Common will expire in 5 days'
    )
    collector = F5SecurityCollector()
    event = collector.parse_syslog_line(sample_log_line)
    assert event is not None
    assert event.source_device == "F5 BIG-IP"
    assert event.category == ThreatCategory.SYSTEM_HEALTH
    assert "Certificate" in event.threat_name
    assert "5 days" in event.threat_name
    assert event.timestamp.day == 6


def test_f5_interval_filtering_and_pagination(monkeypatch):
    monkeypatch.setenv("MNE_F5_CREDENTIAL_REF", "fixture-auth-token")
    auth_credential = os.environ["MNE_F5_CREDENTIAL_REF"]
    collector = F5SecurityCollector(host="172.23.70.89", password=auth_credential)
    req = CollectorRequest(
        start_time=f"{datetime.now(timezone.utc).year}-09-06T00:00:00Z",
        end_time=f"{datetime.now(timezone.utc).year}-09-06T12:00:00Z",
        max_records=1,
    )

    mock_client = MagicMock()
    asm_output = (
        b"Sep  6 03:15:22 f5-core ASM: Attack detected: Support ID: 101, Client IP: 1.1.1.1, Violations: SQLi, Action: Blocked, URL: /test1\n"
        b"Sep  6 04:15:22 f5-core ASM: Attack detected: Support ID: 102, Client IP: 1.1.1.2, Violations: XSS, Action: Blocked, URL: /test2\n"
    )
    mock_stdout = MagicMock()
    mock_stdout.read.return_value = asm_output
    mock_client.exec_command.return_value = (MagicMock(), mock_stdout, MagicMock())

    with patch("paramiko.SSHClient", return_value=mock_client):
        result = collector.collect_logs(request=req)
        assert result.status == CollectorStatus.SUCCESS
        # Only 1 record retrieved due to max_records=1 limit
        assert len(result.events) == 1
        assert result.diagnostic.pagination["has_more"] is True
        assert result.diagnostic.diagnostic_code == "OK"


def test_f5_rotated_logs_and_category_filtering(monkeypatch):
    monkeypatch.setenv("MNE_F5_CREDENTIAL_REF", "fixture-auth-token")
    auth_credential = os.environ["MNE_F5_CREDENTIAL_REF"]
    collector = F5SecurityCollector(host="172.23.70.89", password=auth_credential)
    req = CollectorRequest(
        start_time=f"{datetime.now(timezone.utc).year}-09-06T00:00:00Z",
        end_time=f"{datetime.now(timezone.utc).year}-09-06T12:00:00Z",
        max_records=10,
        categories=["WAF_EXPLOIT"],
    )

    mock_client = MagicMock()
    asm_output = (
        b"Sep  6 03:15:22 f5-core ASM: Attack detected: Support ID: 101, Client IP: 1.1.1.1, Violations: SQLi, Action: Blocked, URL: /test1\n"
    )
    ltm_output = (
        b"Sep  6 04:00:10 f5-core warning mcpd[8123]: 0107143a:4: Certificate test.crt in /Common will expire in 5 days\n"
    )

    def exec_side_effect(cmd, timeout=None):
        m_out = MagicMock()
        if "asm" in cmd:
            m_out.read.return_value = asm_output
        else:
            m_out.read.return_value = ltm_output
        return (MagicMock(), m_out, MagicMock())

    mock_client.exec_command.side_effect = exec_side_effect

    with patch("paramiko.SSHClient", return_value=mock_client):
        result = collector.collect_logs(request=req)
        assert result.status == CollectorStatus.SUCCESS
        assert len(result.events) == 1
        assert result.events[0].category == ThreatCategory.WAF_EXPLOIT
        assert "/var/log/asm*" in result.diagnostic.source_queried
