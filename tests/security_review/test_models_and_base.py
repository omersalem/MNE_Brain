# tests/security_review/test_models_and_base.py
import pytest
from datetime import datetime, timezone, timedelta
from core.connectors.security.models import (
    SeverityLevel,
    ThreatCategory,
    NormalizedSecurityEvent,
    Incident,
    CollectorStatus,
    CollectorResult,
    CollectorRequest,
)
from core.connectors.security.base import BaseSecurityCollector
from core.security_review.contracts import (
    DiagnosticStage,
    DiagnosticStatus,
)


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
        raw_snippet="login failed for user admin",
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
        action_taken="DROPPED",
    )
    assert incident.severity == SeverityLevel.HIGH
    assert incident.incident_id == "MNE-SEC-20260906-01"


def test_collector_request_time_window():
    req = CollectorRequest(
        start_time="2026-09-01T00:00:00Z",
        end_time="2026-09-02T00:00:00Z",
        max_records=100,
    )
    start_dt, end_dt = req.get_time_window()
    assert start_dt == datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert end_dt == datetime(2026, 9, 2, 0, 0, 0, tzinfo=timezone.utc)

    # With hours_back fallback
    ref_now = datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)
    req2 = CollectorRequest(hours_back=6)
    s2, e2 = req2.get_time_window(now=ref_now)
    assert e2 == ref_now
    assert s2 == ref_now - timedelta(hours=6)


def test_base_collector_timeout_and_fault_isolation():
    class MockFailingCollector(BaseSecurityCollector):
        def _fetch_logs_internal(self, hours_back: int):
            raise TimeoutError("Device timed out")

    collector = MockFailingCollector(device_name="TestDevice", timeout=2)
    result = collector.collect_logs(hours_back=24)
    assert result.status == CollectorStatus.FAILED
    assert "Device timed out" in result.error_message
    assert result.events == []
    assert result.diagnostic is not None
    assert result.diagnostic.stage == DiagnosticStage.CONNECTION
    assert result.diagnostic.diagnostic_code == "TIMEOUT"


def test_base_collector_diagnostic_stages():
    # 1. ConnectionRefused -> CONNECTION stage, CONNECTION_FAILED
    class MockConnCollector(BaseSecurityCollector):
        def _fetch_logs_internal(self, hours_back: int):
            raise ConnectionRefusedError("Connection refused by firewall")

    res_conn = MockConnCollector(device_name="FortiGate").collect_logs(24)
    assert res_conn.diagnostic.stage == DiagnosticStage.CONNECTION
    assert res_conn.diagnostic.diagnostic_code == "CONNECTION_FAILED"

    # 2. PermissionError -> AUTHENTICATION stage, AUTH_FAILED
    class MockAuthCollector(BaseSecurityCollector):
        def _fetch_logs_internal(self, hours_back: int):
            raise PermissionError("HTTP 401 Unauthorized")

    res_auth = MockAuthCollector(device_name="Cisco FMC").collect_logs(24)
    assert res_auth.diagnostic.stage == DiagnosticStage.AUTHENTICATION
    assert res_auth.diagnostic.diagnostic_code == "AUTH_FAILED"

    # 3. Parse error -> PARSE stage, PARSE_ERROR
    class MockParseCollector(BaseSecurityCollector):
        def _fetch_logs_internal(self, hours_back: int):
            raise ValueError("Invalid JSON in log output")

    res_parse = MockParseCollector(device_name="Active Directory").collect_logs(24)
    assert res_parse.diagnostic.stage == DiagnosticStage.PARSE
    assert res_parse.diagnostic.diagnostic_code == "PARSE_ERROR"


def test_base_collector_zero_event_explanation():
    class MockEmptyCollector(BaseSecurityCollector):
        def _fetch_logs_internal(self, hours_back: int):
            return []

    collector = MockEmptyCollector(device_name="Sophos Email")
    result = collector.collect_logs(hours_back=12)
    assert result.status == CollectorStatus.SUCCESS
    assert result.diagnostic.diagnostic_code == "QUERY_EMPTY_ZERO_SOURCE"
    assert "zero records" in result.diagnostic.message.lower()


def test_base_collector_cancellation():
    class MockNeverEndingCollector(BaseSecurityCollector):
        def _fetch_logs_internal(self, hours_back: int):
            return []

    req = CollectorRequest(cancel_callback=lambda: True)
    collector = MockNeverEndingCollector(device_name="FortiAnalyzer")
    result = collector.collect_logs(request=req)
    assert result.status == CollectorStatus.SKIPPED
    assert result.diagnostic.status == DiagnosticStatus.CANCELLED
    assert result.diagnostic.diagnostic_code == "CANCELLED"
