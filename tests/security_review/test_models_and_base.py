# tests/security_review/test_models_and_base.py
import pytest
from datetime import datetime, timezone
from core.connectors.security.models import (
    SeverityLevel,
    ThreatCategory,
    NormalizedSecurityEvent,
    Incident,
    CollectorStatus,
    CollectorResult,
)
from core.connectors.security.base import BaseSecurityCollector

def test_models_instantiation():
    event = NormalizedSecurityEvent(
        event_id="evt-123",
        timestamp=datetime.now(timezone.utc),
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        threat_name="SSL-VPN Failed Logon",
        attacker_ip="185.220.101.5",
        target="vpn.mne.gov.ps",
        action_taken="DROPPED",
        count=15,
        raw_snippet="login failed for user admin"
    )
    assert event.source_device == "FortiGate"
    assert event.count == 15

    incident = Incident(
        incident_id="MNE-SEC-20260906-01",
        title="Repeated SSL-VPN Brute Force",
        severity=SeverityLevel.HIGH,
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        attacker_ip="185.220.101.5",
        target="vpn.mne.gov.ps",
        event_count=15,
        first_seen=event.timestamp,
        last_seen=event.timestamp,
        description="Persistent brute-force attack on SSL-VPN endpoint",
        action_taken="DROPPED"
    )
    assert incident.severity == SeverityLevel.HIGH
    assert incident.incident_id == "MNE-SEC-20260906-01"

def test_base_collector_timeout_and_fault_isolation():
    class MockFailingCollector(BaseSecurityCollector):
        def _fetch_logs_internal(self, hours_back: int):
            raise TimeoutError("Device timed out")

    collector = MockFailingCollector(device_name="TestDevice", timeout=2)
    result = collector.collect_logs(hours_back=24)
    assert result.status == CollectorStatus.FAILED
    assert "Device timed out" in result.error_message
    assert result.events == []
