from datetime import datetime, timezone, timedelta
from core.connectors.security.models import (
    NormalizedSecurityEvent,
    ThreatCategory,
    SeverityLevel,
    CollectorResult,
    CollectorStatus,
)
from core.security_review.engine import SecurityRiskEngine

def test_deduplication_of_event_floods():
    now = datetime.now(timezone.utc)
    events = [
        NormalizedSecurityEvent(
            event_id=f"evt-{i}",
            timestamp=now - timedelta(minutes=i),
            source_device="FortiGate",
            category=ThreatCategory.BRUTE_FORCE,
            threat_name="SSL-VPN Failed Logon",
            attacker_ip="185.220.101.5",
            target="admin",
            action_taken="DROPPED"
        )
        for i in range(50)
    ]
    engine = SecurityRiskEngine()
    incidents = engine.process_events(events)
    # Should collapse 50 identical attacks into 1 incident with event_count=50
    assert len(incidents) == 1
    assert incidents[0].event_count == 50
    assert incidents[0].severity == SeverityLevel.HIGH
    assert incidents[0].attacker_ip == "185.220.101.5"

def test_critical_unblocked_malware():
    now = datetime.now(timezone.utc)
    events = [
        NormalizedSecurityEvent(
            event_id="crit-1",
            timestamp=now,
            source_device="Sophos Email",
            category=ThreatCategory.MALWARE,
            threat_name="Ransomware.LockBit payload detected",
            target="dg-finance@mne.gov.ps",
            action_taken="ALLOWED" # Unblocked!
        )
    ]
    engine = SecurityRiskEngine()
    incidents = engine.process_events(events)
    assert len(incidents) == 1
    assert incidents[0].severity == SeverityLevel.CRITICAL

def test_cross_device_attack_correlation():
    now = datetime.now(timezone.utc)
    # Same attacking IP hitting both FortiGate VPN and F5 WAF
    attacker = "194.26.29.112"
    ev1 = NormalizedSecurityEvent(
        event_id="e1",
        timestamp=now - timedelta(minutes=30),
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        threat_name="SSL-VPN Login Fail",
        attacker_ip=attacker,
        target="admin",
        action_taken="DROPPED"
    )
    ev2 = NormalizedSecurityEvent(
        event_id="e2",
        timestamp=now - timedelta(minutes=10),
        source_device="F5 BIG-IP",
        category=ThreatCategory.WAF_EXPLOIT,
        threat_name="SQL-Injection on login.aspx",
        attacker_ip=attacker,
        target="/portal/login.aspx",
        action_taken="BLOCKED"
    )
    engine = SecurityRiskEngine()
    incidents = engine.process_events([ev1, ev2])
    correlated = [inc for inc in incidents if inc.attacker_ip == attacker]
    assert len(correlated) >= 1
    # Check that multi-vector flag or elevated severity is present
    multi_device_notes = [inc for inc in correlated if "Multi-Device" in inc.title or inc.event_count >= 2]
    assert len(multi_device_notes) > 0
