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


def test_multi_branch_attack_correlation():
    now = datetime.now(timezone.utc)
    attacker = "198.51.100.99"
    ev1 = NormalizedSecurityEvent(
        event_id="faz-1",
        timestamp=now - timedelta(minutes=20),
        source_device="FortiAnalyzer",
        category=ThreatCategory.INTRUSION,
        threat_name="[FW-MNE-Hebron] IPS Attack: Apache.Log4j.RCE",
        attacker_ip=attacker,
        target="172.27.13.62",
        action_taken="DROPPED",
        metadata={"reporting_firewall": "FW-MNE-Hebron", "devname": "FW-MNE-Hebron", "faz_crlevel": "critical"},
    )
    ev2 = NormalizedSecurityEvent(
        event_id="faz-2",
        timestamp=now - timedelta(minutes=5),
        source_device="FortiAnalyzer",
        category=ThreatCategory.INTRUSION,
        threat_name="[FW-MNE-Nablus] IPS Attack: Apache.Log4j.RCE",
        attacker_ip=attacker,
        target="172.27.13.58",
        action_taken="DROPPED",
        metadata={"reporting_firewall": "FW-MNE-Nablus", "devname": "FW-MNE-Nablus", "faz_crlevel": "critical"},
    )
    engine = SecurityRiskEngine()
    incidents = engine.process_events([ev1, ev2])

    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.attacker_ip == attacker
    assert inc.event_count == 2
    assert inc.severity == SeverityLevel.CRITICAL
    assert "[Multi-Branch Coordinated Campaign]" in inc.title
    assert "FW-MNE-Hebron" in inc.description
    assert "FW-MNE-Nablus" in inc.description


def test_stable_fingerprint_across_dates():
    """Verifies that the same recurring incident produces the identical fingerprint across different run dates."""
    date1 = datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc)
    date2 = datetime(2026, 9, 9, 14, 0, tzinfo=timezone.utc)

    ev1 = NormalizedSecurityEvent(
        event_id="e-day1",
        timestamp=date1,
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        threat_name="SSL-VPN Failed Logon",
        attacker_ip="185.220.101.5",
        target="admin",
        action_taken="DROPPED",
    )
    ev2 = NormalizedSecurityEvent(
        event_id="e-day2",
        timestamp=date2,
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        threat_name="SSL-VPN Failed Logon",
        attacker_ip="185.220.101.5",
        target="admin",
        action_taken="DROPPED",
    )

    engine = SecurityRiskEngine()
    inc1 = engine.process_events([ev1])[0]
    inc2 = engine.process_events([ev2])[0]

    assert inc1.fingerprint != ""
    assert inc1.fingerprint == inc2.fingerprint, "Fingerprint must be stable and deterministic across dates"


def test_distinct_signatures_not_merged_on_same_ip():
    """Verifies that different exploit signatures on the same IP are NOT collapsed into one incident."""
    now = datetime.now(timezone.utc)
    attacker = "192.0.2.77"

    ev1 = NormalizedSecurityEvent(
        event_id="sig-sqli",
        timestamp=now - timedelta(minutes=15),
        source_device="F5 BIG-IP",
        category=ThreatCategory.WAF_EXPLOIT,
        threat_name="SQL-Injection in login field",
        attacker_ip=attacker,
        target="/login",
        action_taken="BLOCKED",
    )
    ev2 = NormalizedSecurityEvent(
        event_id="sig-log4j",
        timestamp=now - timedelta(minutes=5),
        source_device="F5 BIG-IP",
        category=ThreatCategory.WAF_EXPLOIT,
        threat_name="Apache Log4j RCE exploit attempt",
        attacker_ip=attacker,
        target="/api/query",
        action_taken="BLOCKED",
    )

    engine = SecurityRiskEngine()
    incidents = engine.process_events([ev1, ev2])

    assert len(incidents) == 2, "Unrelated exploit signatures must not be collapsed merely because IP matches"
    signatures = {inc.signature_family for inc in incidents}
    assert "sqli" in signatures
    assert "log4j" in signatures
    assert incidents[0].fingerprint != incidents[1].fingerprint


def test_preservation_of_correlation_details():
    """Verifies that all required correlation fields (devices, targets, event IDs, counts, rationale) are preserved."""
    now = datetime.now(timezone.utc)
    events = [
        NormalizedSecurityEvent(
            event_id="ev-101",
            timestamp=now - timedelta(minutes=10),
            source_device="FortiGate",
            category=ThreatCategory.INTRUSION,
            threat_name="IPS Attack: Apache.Log4j.RCE",
            attacker_ip="203.0.113.50",
            target="172.27.13.62",
            action_taken="DROPPED",
            count=3,
        ),
        NormalizedSecurityEvent(
            event_id="ev-102",
            timestamp=now - timedelta(minutes=2),
            source_device="FortiGate",
            category=ThreatCategory.INTRUSION,
            threat_name="IPS Attack: Apache.Log4j.RCE",
            attacker_ip="203.0.113.50",
            target="172.27.13.62",
            action_taken="ALLOWED",
            count=1,
        ),
    ]

    engine = SecurityRiskEngine()
    incidents = engine.process_events(events)

    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.event_count == 4
    assert inc.blocked_count == 3
    assert inc.allowed_count == 1
    assert inc.action_taken == "ALLOWED"  # Allowed threat overrides
    assert inc.severity == SeverityLevel.CRITICAL
    assert "ev-101" in inc.supporting_event_ids
    assert "ev-102" in inc.supporting_event_ids
    assert "172.27.13.62" in inc.affected_targets
    assert "FortiGate" in inc.devices_involved
    assert "ALLOWED" in inc.observed_dispositions
    assert "BLOCKED" in inc.observed_dispositions
    assert inc.severity_rationale != ""
    assert "Unblocked active" in inc.severity_rationale or "allowed" in inc.severity_rationale.lower()


def test_case_insensitive_action_normalization():
    """Verifies that case variations and synonyms in action_taken are properly normalized."""
    from core.connectors.security.models import normalize_action

    assert normalize_action("allowed") == "ALLOWED"
    assert normalize_action("PASS") == "ALLOWED"
    assert normalize_action("permit") == "ALLOWED"
    assert normalize_action("BLOCKED") == "BLOCKED"
    assert normalize_action("drop") == "BLOCKED"
    assert normalize_action("Denied") == "BLOCKED"
    assert normalize_action("quarantined") == "BLOCKED"
    assert normalize_action("Alert") == "ALERT"
    assert normalize_action("detected") == "ALERT"
    assert normalize_action("unknown_gibberish") == "UNKNOWN"


def test_low_and_info_severity_support():
    """Verifies that Low and Info severities can be assigned without forcing everything to Medium."""
    now = datetime.now(timezone.utc)
    ev_low = NormalizedSecurityEvent(
        event_id="low-1",
        timestamp=now,
        source_device="Active Directory",
        category=ThreatCategory.BRUTE_FORCE,
        threat_name="Failed logon attempt",
        attacker_ip="10.10.1.5",
        target="jdoe",
        action_taken="DROPPED",
        count=2,  # Low volume (< 5)
    )
    ev_info = NormalizedSecurityEvent(
        event_id="info-1",
        timestamp=now,
        source_device="Cisco FMC",
        category=ThreatCategory.SYSTEM_HEALTH,
        threat_name="Routine system backup audit log",
        attacker_ip=None,
        target="System",
        action_taken="ALLOWED",
        count=1,
    )

    engine = SecurityRiskEngine()
    incidents = engine.process_events([ev_low, ev_info])

    sev_map = {inc.title: inc.severity for inc in incidents}
    assert any(sev == SeverityLevel.LOW for sev in sev_map.values())
    assert any(sev == SeverityLevel.INFO for sev in sev_map.values())
