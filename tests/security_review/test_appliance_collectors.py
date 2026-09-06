from datetime import datetime, timezone
from core.connectors.security.fmc_collector import FmcSecurityCollector
from core.connectors.security.sophos_collector import SophosEmailCollector
from core.connectors.security.models import ThreatCategory

def test_fmc_intrusion_parsing():
    sample_fmc_item = {
        "id": "fmc-event-101",
        "timestamp": 1788680000,
        "sourceIp": "45.155.205.233",
        "destinationIp": "172.23.200.2",
        "ruleMessage": "SERVER-WEBAPP Apache Log4j remote code execution attempt",
        "classification": "Attempted Administrator Privilege Gain",
        "impact": "Red",
        "action": "Block"
    }
    collector = FmcSecurityCollector()
    event = collector.parse_fmc_event(sample_fmc_item)
    assert event.source_device == "Cisco FMC"
    assert event.category == ThreatCategory.INTRUSION
    assert event.attacker_ip == "45.155.205.233"
    assert event.action_taken == "BLOCKED"
    assert "Log4j" in event.threat_name

def test_fmc_security_intelligence_parsing():
    sample_si_item = {
        "id": "fmc-si-202",
        "timestamp": 1788681000,
        "sourceIp": "194.26.29.112",
        "destinationIp": "172.23.70.254",
        "ruleMessage": "Security Intelligence Block: Known Command and Control (C2) Server",
        "action": "Drop"
    }
    collector = FmcSecurityCollector()
    event = collector.parse_fmc_event(sample_si_item)
    assert event.source_device == "Cisco FMC"
    assert event.category == ThreatCategory.INTRUSION
    assert event.attacker_ip == "194.26.29.112"
    assert event.action_taken == "BLOCKED"

def test_sophos_email_quarantine_parsing():
    sample_quarantine_entry = {
        "mail_id": "sp-998811",
        "sender": "attacker@compromised-gov.com",
        "recipient": "minister-office@mne.gov.ps",
        "reason": "Malware detected: Trojan.VBS.Agent",
        "sandbox_verdict": "Malicious",
        "action": "Quarantined",
        "timestamp": "2026-09-06T02:45:00Z"
    }
    collector = SophosEmailCollector()
    event = collector.parse_quarantine_entry(sample_quarantine_entry)
    assert event.source_device == "Sophos Email"
    assert event.category == ThreatCategory.MALWARE
    assert event.target == "minister-office@mne.gov.ps"
    assert event.action_taken == "QUARANTINED"
    assert "Trojan" in event.threat_name

def test_sophos_spam_burst_parsing():
    sample_entry = {
        "mail_id": "sp-112233",
        "sender": "spammer@bulk-mailer.biz",
        "recipient": "all-staff@mne.gov.ps",
        "reason": "High confidence Spam surge",
        "action": "Dropped",
        "timestamp": "2026-09-06T03:00:00Z"
    }
    collector = SophosEmailCollector()
    event = collector.parse_quarantine_entry(sample_entry)
    assert event.source_device == "Sophos Email"
    assert event.category == ThreatCategory.PHISHING
    assert event.action_taken == "DROPPED"
