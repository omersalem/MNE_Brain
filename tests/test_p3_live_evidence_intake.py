#!/usr/bin/env python3
"""Offline acceptance tests for bounded P2 evidence intake into P3 and P4."""

import hashlib
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path


base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.incidents.case_manager import IncidentCaseManager
from core.orchestration.incident_orchestrator import IncidentOrchestrator


def _record(check_id: str, content: str, *, expired: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    observed = now - timedelta(minutes=20 if expired else 1)
    expires = now - timedelta(minutes=1) if expired else now + timedelta(minutes=14)
    evidence_id = f"ev-live-{hashlib.sha256((check_id + content).encode()).hexdigest()[:16]}"
    return {
        "evidence_id": evidence_id,
        "entity_id": "fw-fortigate-edge-01",
        "profile_name": "fortigate_edge",
        "platform": "fortinet_fortios",
        "source_file": f"live-adapter://fortigate_ssh_readonly/{check_id}",
        "source": "owner-authorized read-only transport",
        "evidence_status": "live_verified",
        "trust_level": 5,
        "observed_at": observed.isoformat(),
        "expires_at": expires.isoformat(),
        "evidence_refs": [evidence_id],
        "verification_target": "fw-fortigate-edge-01",
        "verification_check_id": check_id,
        "verification_outcome": "success",
        "scope_reference": "P3-INTAKE-FIXTURE",
        "transport_status": "SUCCESS",
        "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
        "heading": f"Fixture {check_id}",
        "content": content,
    }


def _envelope(records: list[dict]) -> dict:
    return {
        "status": "SUCCESS",
        "profile_name": "fortigate_edge",
        "platform": "fortinet_fortios",
        "adapter_id": "fortigate_ssh_readonly",
        "entity_id": "fw-fortigate-edge-01",
        "trust_level": 5,
        "checks_executed": len(records),
        "checks_attempted": len(records),
        "telemetry_results": records,
        "failures": [],
        "connection_attempted": True,
        "simulation_mode": False,
        "raw_output_returned": False,
        "credential_returned": False,
        "persistence": "NOT_REQUESTED",
    }


def test_p3_accepts_fresh_p2_evidence_without_inventing_interface_root_cause() -> None:
    records = [
        _record("system_status", "Hostname: FG-MNE\nOperation Mode: NAT"),
        _record("interface_stats", "==[port1]\nstatus: up\n==[port9]\nstatus: down"),
    ]
    result = IncidentOrchestrator(base_dir=base_dir).investigate(
        "Assess current evidence for fw-fortigate-edge-01",
        verification_result=_envelope(records),
    )

    assert result["metrics"]["accepted_evidence"] == 2
    assert result["reasoning"]["accepted_evidence_refs"] == sorted(
        record["evidence_id"] for record in records
    )
    assert result["reasoning"]["reasoning_status"] == "PENDING_EVIDENCE"
    assert result["reasoning"]["conclusive_root_cause"] is None
    assert any(
        "affected-port correlation" in item["reason"]
        for item in result["reasoning"]["evidence_assessment"]
    )
    assert not any(result["safety"].values())


def test_p3_rejects_stale_wrong_target_and_simulated_evidence() -> None:
    stale = IncidentOrchestrator(base_dir=base_dir).investigate(
        "Assess current evidence for fw-fortigate-edge-01",
        verification_result=_envelope([_record("system_status", "stale", expired=True)]),
    )
    wrong_target_envelope = _envelope([_record("system_status", "current")])
    wrong_target_envelope["entity_id"] = "fw-fortigate-hq-01"
    wrong = IncidentOrchestrator(base_dir=base_dir).investigate(
        "Assess current evidence for fw-fortigate-edge-01",
        verification_result=wrong_target_envelope,
    )
    simulated_envelope = _envelope([_record("system_status", "current")])
    simulated_envelope["simulation_mode"] = True
    simulated = IncidentOrchestrator(base_dir=base_dir).investigate(
        "Assess current evidence for fw-fortigate-edge-01",
        verification_result=simulated_envelope,
    )

    assert stale["metrics"]["accepted_evidence"] == 0
    assert wrong["metrics"]["accepted_evidence"] == 0
    assert simulated["metrics"]["accepted_evidence"] == 0


def test_p3_deduplicates_replayed_evidence() -> None:
    record = _record("system_status", "Hostname: FG-MNE")
    result = IncidentOrchestrator(base_dir=base_dir).investigate(
        "Assess current evidence for fw-fortigate-edge-01",
        verification_result=_envelope([record, deepcopy(record)]),
    )

    assert result["metrics"]["accepted_evidence"] == 1
    assert any("Duplicate supplemental evidence" in item for item in result["evidence_pack"]["unknowns"])


def test_p4_consumes_p3_result_without_persistence_or_notification() -> None:
    envelope = _envelope([_record("system_status", "Hostname: FG-MNE")])
    case = IncidentCaseManager(base_dir=base_dir).build_case(
        "Assess current evidence for fw-fortigate-edge-01",
        verification_result=envelope,
    )

    assert case["investigation"]["metrics"]["accepted_evidence"] == 1
    assert case["case_state"] == "IMPACT_REQUIRED"
    assert case["handoff_packet"]["accepted_evidence_refs"]
    assert not any(case["safety"].values())
