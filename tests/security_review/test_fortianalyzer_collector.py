import pytest
from datetime import datetime, timezone
from core.connectors.security.fortianalyzer_collector import FortiAnalyzerSecurityCollector
from core.connectors.security.models import CollectorStatus, ThreatCategory


def test_faz_key_value_parsing():
    collector = FortiAnalyzerSecurityCollector()
    line = 'date=2026-09-07 time=10:15:30 devname="FW-MNE-Hebron" logid="0100012345" type="ips" srcip=185.220.101.5 msg="IPS signature match"'
    kv = collector.parse_key_value_pairs(line)
    assert kv["date"] == "2026-09-07"
    assert kv["devname"] == "FW-MNE-Hebron"
    assert kv["srcip"] == "185.220.101.5"
    assert kv["msg"] == "IPS signature match"


def test_faz_ips_attack_parsing():
    collector = FortiAnalyzerSecurityCollector()
    sample_log = (
        'date=2026-09-07 time=08:30:12 devname="FW-MNE-Hebron" devid="FGT71GTK25009263" '
        'logid="0419016384" type="utm" subtype="ips" level="critical" crlevel="critical" '
        'action="dropped" srcip=45.155.205.233 dstip=172.27.13.62 attack="Apache.Log4j.RCE" '
        'msg="Apache Log4j Remote Code Execution Exploit Attempt"'
    )
    event = collector.parse_log_line(sample_log)
    assert event is not None
    assert event.source_device == "FortiAnalyzer"
    assert event.category == ThreatCategory.INTRUSION
    assert event.attacker_ip == "45.155.205.233"
    assert event.target == "172.27.13.62"
    assert event.action_taken == "DROPPED"
    assert "[FW-MNE-Hebron]" in event.threat_name
    assert "Log4j" in event.threat_name
    assert event.metadata.get("reporting_firewall") == "FW-MNE-Hebron"
    assert event.metadata.get("faz_crlevel") == "critical"


def test_faz_malware_parsing():
    collector = FortiAnalyzerSecurityCollector()
    sample_log = (
        'date=2026-09-07 time=09:12:44 devname="FG-MNE" devid="FG4H1FT924905842" '
        'logid="0200008192" type="utm" subtype="virus" level="warning" '
        'action="quarantine" srcip=172.23.71.45 dstip=198.51.100.10 virus="Trojan.Agent.Generic" '
        'msg="File infected with Trojan.Agent.Generic"'
    )
    event = collector.parse_log_line(sample_log)
    assert event is not None
    assert event.source_device == "FortiAnalyzer"
    assert event.category == ThreatCategory.MALWARE
    assert event.action_taken == "DROPPED"
    assert "[FG-MNE]" in event.threat_name
    assert "Trojan.Agent.Generic" in event.threat_name
    assert event.metadata.get("reporting_firewall") == "FG-MNE"


def test_faz_webfilter_block_parsing():
    collector = FortiAnalyzerSecurityCollector()
    sample_log = (
        'date=2026-09-07 time=07:45:00 devname="FW-MNE-Nablus" '
        'logid="0316013056" type="utm" subtype="webfilter" level="alert" '
        'action="blocked" srcip=172.27.13.58 dstip=192.0.2.80 url="malicious-c2-portal.com" '
        'msg="URL blocked because category Malicious Web Sites"'
    )
    event = collector.parse_log_line(sample_log)
    assert event is not None
    assert event.source_device == "FortiAnalyzer"
    assert event.action_taken == "DROPPED"
    assert "[FW-MNE-Nablus]" in event.threat_name
    assert "malicious-c2-portal.com" in event.threat_name


def test_faz_vpn_fail_parsing():
    collector = FortiAnalyzerSecurityCollector()
    sample_log = (
        'date=2026-09-07 time=06:22:15 devname="FW-MNE-Bethlahem" '
        'logid="0101037128" type="event" subtype="vpn" level="alert" '
        'action="tunnel-down" remip=194.26.29.11 user="operator" '
        'reason="negotiation failure" msg="SSL VPN login fail"'
    )
    event = collector.parse_log_line(sample_log)
    assert event is not None
    assert event.source_device == "FortiAnalyzer"
    assert event.category == ThreatCategory.BRUTE_FORCE
    assert event.attacker_ip == "194.26.29.11"
    assert event.target == "operator"
    assert "[FW-MNE-Bethlahem]" in event.threat_name


def test_faz_empty_or_malformed():
    collector = FortiAnalyzerSecurityCollector()
    assert collector.parse_log_line("") is None
    assert collector.parse_log_line("   ") is None
    assert collector.parse_log_line("random non-syslog line without date or logid") is None


def test_faz_missing_credentials_raises():
    collector = FortiAnalyzerSecurityCollector(host="172.23.71.206", password="", api_key="")
    with pytest.raises(ValueError, match="Neither MNE_FORTIANALYZER_PASSWORD nor MNE_FORTIANALYZER_API_KEY"):
        collector._fetch_logs_internal(hours_back=24)


def test_faz_collect_logs_isolation():
    collector = FortiAnalyzerSecurityCollector(host="172.23.71.206", password="", api_key="")
    result = collector.collect_logs(hours_back=24)
    assert result.device_name == "FortiAnalyzer"
    assert result.status == CollectorStatus.FAILED
    assert result.error_message is not None
    assert result.collection_duration_seconds >= 0.0
    assert len(result.events) == 0
