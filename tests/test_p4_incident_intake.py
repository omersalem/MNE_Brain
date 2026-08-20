#!/usr/bin/env python3
"""Acceptance tests for the professional P4 incident-intake boundary."""

import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from core.api import server as api_server
from core.incidents.intake import IncidentIntakeService
from scripts.run_p4_intake_pilot import run_p4_intake_pilot


BASE_DIR = Path(__file__).resolve().parent.parent


def _request(**updates):
    payload = {
        "target_reference": "fw-fortigate-edge-01",
        "symptom": "Remote users cannot reach the published service",
        "affected_service": "SSL VPN",
        "affected_scope": "multiple_users",
        "availability": "unavailable",
        "affected_user_count": 12,
        "incident_reference": "INC-2026-0816-001",
        "reported_at": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(updates)
    return payload


def test_complete_intake_builds_ready_non_persistent_case():
    result = IncidentIntakeService(base_dir=BASE_DIR).create_intake(_request())

    assert result["status"] == "READY_FOR_EVIDENCE_REVIEW"
    assert result["truth_status"] == "REPORTED_NOT_VERIFIED"
    assert result["case"]["target"]["entity_id"] == "fw-fortigate-edge-01"
    assert result["case"]["priority"]["classification"] == "PROVISIONAL_P2"
    assert result["case"]["impact"]["affected_service"] == "SSL VPN"
    assert result["case"]["impact"]["affected_user_count"] == 12
    assert result["intake"]["owner_reference"] == "MNE-BRAIN-OWNER"
    assert result["case"]["ownership"]["primary"]["team"] == "MNE-BRAIN-OWNER"
    assert result["readiness"]["evidence_request_ready"] is True
    assert result["next_evidence_objectives"]
    assert not any(result["safety"].values())


def test_incomplete_impact_and_unknown_target_withhold_evidence_objectives():
    incomplete = IncidentIntakeService(base_dir=BASE_DIR).create_intake(
        _request(affected_scope="unknown", availability="unknown", affected_user_count=None)
    )
    unknown = IncidentIntakeService(base_dir=BASE_DIR).create_intake(
        _request(target_reference="not-a-known-ministry-target")
    )

    assert incomplete["status"] == "IMPACT_REQUIRED"
    assert incomplete["next_evidence_objectives"] == []
    assert incomplete["readiness"]["evidence_request_ready"] is False
    assert unknown["status"] == "NEEDS_TARGET"
    assert unknown["case"]["target"] is None
    assert unknown["next_evidence_objectives"] == []


@pytest.mark.parametrize(
    "updates, message",
    [
        ({"affected_scope": "branch", "branch_references": []}, "exactly one branch"),
        (
            {"affected_scope": "multiple_branches", "branch_references": ["nablus"]},
            "at least two branch",
        ),
        ({"affected_scope": "single_user", "affected_user_count": 2}, "equal to 1"),
        ({"affected_scope": "multiple_users", "affected_user_count": 1}, "at least 2"),
        ({"unexpected": "field"}, "Additional properties"),
        (
            {"reported_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()},
            "cannot be in the future",
        ),
    ],
)
def test_invalid_or_inconsistent_intake_fails_closed(updates, message):
    with pytest.raises(ValueError, match=message):
        IncidentIntakeService(base_dir=BASE_DIR).create_intake(_request(**updates))


def test_sole_owner_requires_no_department_or_approval_input():
    result = IncidentIntakeService(base_dir=BASE_DIR).create_intake(_request())

    assert result["readiness"]["owner_controlled"] is True
    assert result["case"]["ownership"]["routing_status"] == "OWNER_CONTROLLED_NOT_NOTIFIED"
    assert result["workflow_governance"]["owner_reference"] == "MNE-BRAIN-OWNER"
    assert result["safety"]["notification_sent"] is False


def test_dedicated_api_delegates_without_live_execution_or_persistence():
    post_source = inspect.getsource(api_server.MNEBrainAPIHandler.do_POST)
    handler_source = inspect.getsource(
        api_server.MNEBrainAPIHandler._handle_incident_intake
    )

    assert '"/api/incidents/intake"' in post_source
    assert "IncidentIntakeService" in handler_source
    assert "P4_INTAKE_REJECTED" in handler_source
    assert "execute_live_verification" not in handler_source
    assert "save" not in handler_source.casefold()


def test_incident_intake_pilot_covers_professional_boundary():
    result = run_p4_intake_pilot()

    assert result["success"] is True
    assert result["passed"] == result["total"] == 12
