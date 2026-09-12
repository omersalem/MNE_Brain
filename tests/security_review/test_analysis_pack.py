"""
Unit tests for SecurityAnalysisPackBuilder (Batch 5).
Verifies bounded, schema-valid context packs for Codex and Antigravity AI analysis.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from core.connectors.security.models import Incident, SeverityLevel, ThreatCategory
from core.security_review.analysis_pack import (
    MAX_INCIDENT_PACK_CHARS,
    MAX_RUN_PACK_CHARS,
    SecurityAnalysisPackBuilder,
)
from core.security_review.contracts import (
    ReviewMode,
    RunState,
    SecurityReviewRequest,
    SecurityReviewRun,
    validate_contract,
)
from core.security_review.run_store import SecurityReviewRunStore

BASE = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def run_store(tmp_path):
    store_dir = tmp_path / "runs"
    return SecurityReviewRunStore(store_dir)


@pytest.fixture
def sample_run_with_incidents(run_store):
    run_id = "sec-run-test-pack-001"
    run = SecurityReviewRun(
        run_id=run_id,
        request=SecurityReviewRequest(
            mode=ReviewMode.QUICK,
            collector_ids=["fortigate_core", "f5_bigip"],
        ).to_dict(),
        state=RunState.COMPLETED,
        stage="COMPLETED",
        created_at="2026-09-09T10:00:00+00:00",
        completed_at="2026-09-09T10:05:00+00:00",
        incident_counts={"total": 2, "critical": 1, "high": 1, "medium": 0, "low": 0, "info": 0},
    )
    run_store.save_run(run)

    events = [
        {
            "event_id": f"evt-{i}",
            "timestamp": "2026-09-09T10:01:00+00:00",
            "source_device": "FortiGate-Core-HQ",
            "category": "INTRUSION",
            "threat_name": "SQL Injection Attempt",
            "attacker_ip": "198.51.100.25",
            "target": "10.0.10.50",
            "action_taken": "BLOCKED",
            "count": 1,
            "raw_snippet": "attack_id=12345 msg=SQLi detected",
            "metadata": {},
        }
        for i in range(15)
    ]
    run_store.save_events(run_id, events)

    incidents = [
        Incident(
            incident_id="inc-sqli-001",
            title="SQL Injection Campaign against Portal",
            severity=SeverityLevel.CRITICAL,
            source_device="FortiGate-Core-HQ",
            category=ThreatCategory.INTRUSION,
            first_seen="2026-09-09T10:00:00+00:00",
            last_seen="2026-09-09T10:04:00+00:00",
            description="Repeated SQL injection probes targeting public portal VIP.",
            action_taken="BLOCKED",
            event_count=15,
            attacker_ip="198.51.100.25",
            target="10.0.10.50",
            signature_family="SQL_INJECTION",
            devices_involved=["FortiGate-Core-HQ"],
            branches_involved=["HQ-DataCenter"],
            supporting_event_ids=[f"evt-{i}" for i in range(5)],
        ),
        Incident(
            incident_id="inc-waf-002",
            title="Cross-Site Scripting Probes",
            severity=SeverityLevel.HIGH,
            source_device="F5-BIGIP-External",
            category=ThreatCategory.INTRUSION,
            first_seen="2026-09-09T10:02:00+00:00",
            last_seen="2026-09-09T10:03:00+00:00",
            description="XSS script tags reflected in query parameters.",
            action_taken="ALERT",
            event_count=3,
            attacker_ip="203.0.113.88",
            target="portal.mne.local",
            signature_family="XSS",
            devices_involved=["F5-BIGIP-External"],
            branches_involved=["HQ-DMZ"],
            supporting_event_ids=["evt-waf-1", "evt-waf-2"],
        ),
    ]

    serialized_incidents = []
    for inc in incidents:
        d = {
            "incident_id": inc.incident_id,
            "title": inc.title,
            "severity": inc.severity.value,
            "source_device": inc.source_device,
            "category": inc.category.value,
            "first_seen": inc.first_seen,
            "last_seen": inc.last_seen,
            "description": inc.description,
            "action_taken": inc.action_taken,
            "event_count": inc.event_count,
            "attacker_ip": inc.attacker_ip,
            "target": inc.target,
            "signature_family": inc.signature_family,
            "devices_involved": inc.devices_involved,
            "branches_involved": inc.branches_involved,
            "supporting_event_ids": inc.supporting_event_ids,
        }
        serialized_incidents.append(d)
    run_store.save_incidents(run_id, serialized_incidents)

    # Reconcile in IncidentStore
    run_store.record_run_incidents(run_id, incidents)

    diags = {
        "fortigate_core": {
            "device_name": "FortiGate-Core-HQ",
            "status": "SUCCESS",
            "diagnostic_code": "COLLECTION_SUCCESS",
            "records_fetched": 15,
            "duration_seconds": 1.2,
        },
        "f5_bigip": {
            "device_name": "F5-BIGIP-External",
            "status": "SUCCESS",
            "diagnostic_code": "COLLECTION_SUCCESS",
            "records_fetched": 3,
            "duration_seconds": 0.8,
        },
    }
    run_store.save_collector_diagnostics(run_id, diags)
    return run_id


def test_build_run_pack_conforms_to_schema(run_store, sample_run_with_incidents):
    builder = SecurityAnalysisPackBuilder(run_store=run_store, base_dir=BASE)
    pack = builder.build_run_pack(sample_run_with_incidents)

    assert pack["target_type"] == "RUN"
    assert pack["run_id"] == sample_run_with_incidents
    assert len(pack["incidents"]) == 2
    assert len(pack["collector_diagnostics"]) == 2
    assert isinstance(pack["collector_diagnostics"], list)
    assert len(pack["unknowns"]) > 0
    assert len(pack["sources"]) > 0
    assert pack["character_count"] <= MAX_RUN_PACK_CHARS

    # Validate against JSON Schema
    validate_contract(pack, "security-analysis-pack.schema.json")


def test_build_incident_pack_conforms_to_schema(run_store, sample_run_with_incidents):
    builder = SecurityAnalysisPackBuilder(run_store=run_store, base_dir=BASE)
    incidents, _ = run_store.list_incident_records(limit=1)
    assert len(incidents) == 1
    fp = incidents[0]["fingerprint"]

    pack = builder.build_incident_pack(fp, run_id=sample_run_with_incidents)

    assert pack["target_type"] == "INCIDENT"
    assert pack["incident_fingerprints"] == [fp]
    assert len(pack["incidents"]) == 1
    assert "earlier_occurrences_trend" in pack
    assert pack["character_count"] <= MAX_INCIDENT_PACK_CHARS

    validate_contract(pack, "security-analysis-pack.schema.json")


def test_build_incidents_selection_pack(run_store, sample_run_with_incidents):
    builder = SecurityAnalysisPackBuilder(run_store=run_store, base_dir=BASE)
    incidents, _ = run_store.list_incident_records(limit=2)
    fps = [inc["fingerprint"] for inc in incidents]

    pack = builder.build_incidents_pack(fps, run_id=sample_run_with_incidents)

    assert pack["target_type"] == "INCIDENTS"
    assert set(pack["incident_fingerprints"]) == set(fps)
    assert len(pack["incidents"]) == len(fps)
    assert pack["character_count"] <= MAX_RUN_PACK_CHARS

    validate_contract(pack, "security-analysis-pack.schema.json")


def test_pack_size_budget_enforcement(run_store, sample_run_with_incidents):
    builder = SecurityAnalysisPackBuilder(run_store=run_store, base_dir=BASE)

    # Inject a large event payload
    huge_events = [
        {
            "event_id": f"huge-{i}",
            "timestamp": "2026-09-09T10:00:00+00:00",
            "source_device": "Device-" + ("A" * 50),
            "threat_name": "Threat-" + ("X" * 100),
            "raw_snippet": "Payload=" + ("Z" * 500),
            "category": "INTRUSION",
            "action_taken": "BLOCKED",
            "count": 1,
            "metadata": {"details": "M" * 200},
        }
        for i in range(100)
    ]
    run_store.save_events(sample_run_with_incidents, huge_events)

    pack = builder.build_run_pack(sample_run_with_incidents, max_chars=15000)
    serialized = json.dumps(pack, ensure_ascii=False)

    assert len(serialized) <= 15000
    assert pack["character_count"] <= 15000
    validate_contract(pack, "security-analysis-pack.schema.json")
