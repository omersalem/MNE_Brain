from datetime import datetime, timezone
from core.connectors.security.fortigate_collector import FortiGateSecurityCollector
from core.connectors.security.f5_collector import F5SecurityCollector
from core.connectors.security.models import ThreatCategory

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

def test_fortigate_ips_log_parsing():
    sample_log = (
        'date=2026-09-06 time=05:10:20 devname="FGT-Edge" logid="0419016384" '
        'type="ips" subtype="signature" level="critical" action="dropped" '
        'srcip=45.155.205.233 dstip=172.23.200.2 attack="Apache.Log4j.Error.Log.Remote.Code.Execution" '
        'msg="detected Log4j exploit attempt"'
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
