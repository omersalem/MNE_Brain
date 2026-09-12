"""
Tests for Incident Lifecycle, cross-run tracking, persistence, and trends.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest

from core.connectors.security.models import (
    Incident,
    NormalizedSecurityEvent,
    SeverityLevel,
    ThreatCategory,
)
from core.security_review.engine import SecurityRiskEngine
from core.security_review.incidents import (
    IncidentLifecycleState,
    IncidentRecord,
    IncidentStore,
    generate_fingerprint,
)
from core.security_review.run_store import SecurityReviewRunStore
from core.security_review.trends import compare_runs, get_fleet_trends, get_incident_history


def test_incident_record_schema_validation(tmp_path):
    """Ensures IncidentRecord strictly conforms to security-incident-record.schema.json."""
    record = IncidentRecord(
        fingerprint="inc-test1234567890",
        display_id="MNE-SEC-20260909-01",
        title="Test Brute Force",
        category="BRUTE_FORCE",
        signature_family="brute-force",
        source_device="FortiGate",
        attacker_identity="192.168.1.100",
        target_identity="admin",
        lifecycle_state="NEW",
        current_severity="HIGH",
        peak_severity="HIGH",
    )
    # validate() raises jsonschema.ValidationError if schema fails
    record.validate()


def test_incident_lifecycle_transitions(tmp_path):
    """Tests the full lifecycle: NEW -> RECURRING -> RESOLVED -> REOPENED."""
    store = IncidentStore(tmp_path / "incidents")
    engine = SecurityRiskEngine()
    now = datetime.now(timezone.utc)

    # 1. Run 1 - First occurrence
    ev1 = NormalizedSecurityEvent(
        event_id="e1",
        timestamp=now - timedelta(days=2),
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        threat_name="SSL-VPN Failed Logon",
        attacker_ip="185.220.101.5",
        target="admin",
        action_taken="DROPPED",
        count=10,
    )
    incidents_run1 = engine.process_events([ev1])
    records_run1 = store.record_run_incidents("run-001", incidents_run1)

    assert len(records_run1) == 1
    rec1 = records_run1[0]
    assert rec1.lifecycle_state == IncidentLifecycleState.NEW.value
    assert rec1.occurrence_count == 1
    assert "run-001" in rec1.run_references

    fp = rec1.fingerprint

    # 2. Run 2 - Second occurrence (NEW -> RECURRING)
    ev2 = NormalizedSecurityEvent(
        event_id="e2",
        timestamp=now - timedelta(days=1),
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        threat_name="SSL-VPN Failed Logon",
        attacker_ip="185.220.101.5",
        target="admin",
        action_taken="DROPPED",
        count=15,
    )
    incidents_run2 = engine.process_events([ev2])
    records_run2 = store.record_run_incidents("run-002", incidents_run2)

    assert len(records_run2) == 1
    rec2 = records_run2[0]
    assert rec2.fingerprint == fp
    assert rec2.lifecycle_state == IncidentLifecycleState.RECURRING.value
    assert rec2.occurrence_count == 2
    assert "run-002" in rec2.run_references

    # 3. Analyst sets status to RESOLVED
    rec2.update_status(IncidentLifecycleState.RESOLVED.value, author="analyst-bob", note="IP blocked at border router")
    store.save_incident(rec2)

    loaded = store.get_incident(fp)
    assert loaded.lifecycle_state == IncidentLifecycleState.RESOLVED.value
    assert len(loaded.analyst_notes) == 1
    assert "IP blocked at border router" in loaded.analyst_notes[0]["note"]

    # 4. Run 3 - Threat reappears (RESOLVED -> REOPENED)
    ev3 = NormalizedSecurityEvent(
        event_id="e3",
        timestamp=now,
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        threat_name="SSL-VPN Failed Logon",
        attacker_ip="185.220.101.5",
        target="admin",
        action_taken="DROPPED",
        count=5,
    )
    incidents_run3 = engine.process_events([ev3])
    records_run3 = store.record_run_incidents("run-003", incidents_run3)

    assert len(records_run3) == 1
    rec3 = records_run3[0]
    assert rec3.fingerprint == fp
    assert rec3.lifecycle_state == IncidentLifecycleState.REOPENED.value
    assert rec3.occurrence_count == 3
    assert "run-003" in rec3.run_references
    # Notice note about automatic reopening
    assert any("reopened" in n["note"].lower() for n in rec3.analyst_notes)


def test_persistence_survives_restart(tmp_path):
    """Verifies that incident records and notes survive a full process restart."""
    inc_dir = tmp_path / "incidents"
    store1 = IncidentStore(inc_dir)

    record = IncidentRecord(
        fingerprint="inc-persist-test",
        display_id="MNE-SEC-20260909-02",
        title="Persistent Threat",
        category="MALWARE",
        signature_family="malware",
        source_device="Sophos Email",
        current_severity="HIGH",
        peak_severity="CRITICAL",
    )
    record.add_note("Initial triage by SOC team", author="soc-alice")
    store1.save_incident(record)

    # Simulate restart by instantiating a completely new IncidentStore
    store2 = IncidentStore(inc_dir)
    loaded = store2.get_incident("inc-persist-test")

    assert loaded is not None
    assert loaded.fingerprint == "inc-persist-test"
    assert loaded.title == "Persistent Threat"
    assert loaded.current_severity == "HIGH"
    assert loaded.peak_severity == "CRITICAL"
    assert len(loaded.analyst_notes) == 1
    assert loaded.analyst_notes[0]["author"] == "soc-alice"


def test_compact_index_search_and_filter(tmp_path):
    """Verifies search, category filtering, and status filtering without loading full files."""
    store = IncidentStore(tmp_path / "incidents")

    r1 = IncidentRecord(
        fingerprint="inc-1",
        display_id="MNE-SEC-20260909-01",
        title="Log4j Remote Code Execution",
        category="INTRUSION",
        signature_family="log4j",
        current_severity="CRITICAL",
        lifecycle_state="NEW",
        attacker_identity="198.51.100.5",
    )
    r2 = IncidentRecord(
        fingerprint="inc-2",
        display_id="MNE-SEC-20260909-02",
        title="SQL Injection on login",
        category="WAF_EXPLOIT",
        signature_family="sqli",
        current_severity="HIGH",
        lifecycle_state="INVESTIGATING",
        attacker_identity="198.51.100.6",
    )
    r3 = IncidentRecord(
        fingerprint="inc-3",
        display_id="MNE-SEC-20260909-03",
        title="SSH Brute Force",
        category="BRUTE_FORCE",
        signature_family="brute-force",
        current_severity="LOW",
        lifecycle_state="RESOLVED",
        attacker_identity="10.0.0.1",
    )

    store.save_incident(r1)
    store.save_incident(r2)
    store.save_incident(r3)

    # 1. Severity filter
    crit_list, total_crit = store.list_incidents(severity="CRITICAL")
    assert total_crit == 1
    assert crit_list[0]["fingerprint"] == "inc-1"

    # 2. Status filter
    inv_list, total_inv = store.list_incidents(status="INVESTIGATING")
    assert total_inv == 1
    assert inv_list[0]["fingerprint"] == "inc-2"

    # 3. Search query
    search_list, total_search = store.list_incidents(search="login")
    assert total_search == 1
    assert search_list[0]["fingerprint"] == "inc-2"


def test_incident_timeline_generation(tmp_path):
    """Verifies chronological timeline generation including first seen, subsequent runs, and notes."""
    store = IncidentStore(tmp_path / "incidents")

    record = IncidentRecord(
        fingerprint="inc-tl-001",
        display_id="MNE-SEC-20260909-05",
        title="Repeated Auth Failure",
        category="BRUTE_FORCE",
        signature_family="brute-force",
        first_seen="2026-09-07T10:00:00+00:00",
        last_seen="2026-09-09T12:00:00+00:00",
        run_references=["run-1", "run-2"],
        event_count=25,
        action_taken="DROPPED",
    )
    record.add_note("Investigating gateway logs", author="operator-1")
    record.update_status("INVESTIGATING", author="lead-analyst", note="Active investigation")
    store.save_incident(record)

    timeline = store.get_timeline("inc-tl-001")
    assert len(timeline) >= 4

    types = [t["type"] for t in timeline]
    assert "FIRST_SEEN" in types
    assert "OBSERVATION" in types
    assert "ANALYST_NOTE" in types
    assert "STATUS_CHANGE" in types


def test_cross_run_trends_and_comparison(tmp_path):
    """Verifies compare_runs and get_fleet_trends across simulated runs."""
    run_store = SecurityReviewRunStore(tmp_path / "runs")
    inc_store = run_store.incident_store

    # Create Run 1 with Incident A and Incident B
    inc_a = {
        "fingerprint": "inc-a",
        "display_id": "MNE-SEC-01",
        "title": "Threat A",
        "category": "INTRUSION",
        "current_severity": "MEDIUM",
        "event_count": 5,
    }
    inc_b = {
        "fingerprint": "inc-b",
        "display_id": "MNE-SEC-02",
        "title": "Threat B",
        "category": "MALWARE",
        "current_severity": "HIGH",
        "event_count": 10,
    }
    run_store.save_incidents("run-A", [inc_a, inc_b])

    # Create Run 2 with Incident B (elevated to CRITICAL) and new Incident C
    inc_b_elevated = dict(inc_b, current_severity="CRITICAL", event_count=20)
    inc_c = {
        "fingerprint": "inc-c",
        "display_id": "MNE-SEC-03",
        "title": "Threat C",
        "category": "WAF_EXPLOIT",
        "current_severity": "HIGH",
        "event_count": 2,
    }
    run_store.save_incidents("run-B", [inc_b_elevated, inc_c])

    comparison = compare_runs("run-A", "run-B", run_store, inc_store)

    assert len(comparison["new_incidents"]) == 1
    assert comparison["new_incidents"][0]["fingerprint"] == "inc-c"

    assert len(comparison["resolved_incidents"]) == 1
    assert comparison["resolved_incidents"][0]["fingerprint"] == "inc-a"

    assert len(comparison["persisting_incidents"]) == 1
    assert comparison["persisting_incidents"][0]["fingerprint"] == "inc-b"

    assert len(comparison["severity_changes"]) == 1
    assert comparison["severity_changes"][0]["fingerprint"] == "inc-b"
    assert comparison["severity_changes"][0]["prior_severity"] == "HIGH"
    assert comparison["severity_changes"][0]["current_severity"] == "CRITICAL"

    assert comparison["metrics"]["event_count_delta"] == 7  # 22 - 15 = 7
