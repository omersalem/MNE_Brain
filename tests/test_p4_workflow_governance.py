#!/usr/bin/env python3
"""Acceptance tests for the minimal sole-owner P4 governance model."""

import inspect
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import pytest

from core.api import server as api_server
from core.incidents.intake import IncidentIntakeService
from core.incidents.workflow_governance import IncidentWorkflowGovernance
from scripts.run_p4_workflow_governance_pilot import (
    run_p4_workflow_governance_pilot,
)


BASE_DIR = Path(__file__).resolve().parent.parent


def test_governance_status_is_schema_valid_and_owner_controlled():
    evaluator = IncidentWorkflowGovernance(base_dir=BASE_DIR)
    result = evaluator.evaluate()

    jsonschema.validate(instance=result, schema=evaluator.schema)
    assert result["mode"] == "SOLE_OWNER_GOVERNANCE"
    assert result["approval_state"] == "OWNER_CONTROLLED"
    assert result["owner_reference"] == "MNE-BRAIN-OWNER"
    assert result["audit_mode"] == "IN_MEMORY_ONLY"
    assert result["retention"] == "NONE"
    assert not any(result["disabled_capabilities"].values())
    assert not any(result["safety"].values())


def test_authorization_rules_match_explicit_owner_instructions():
    result = IncidentWorkflowGovernance(base_dir=BASE_DIR).evaluate()

    assert result["authorization"] == {
        "read_only_troubleshooting": "EXPLICIT_OWNER_PROCEED",
        "configuration_changes": "EXPLICIT_OWNER_INSTRUCTION",
        "remediation": "EXPLICIT_OWNER_INSTRUCTION",
    }


@pytest.mark.parametrize(
    "field, value",
    [
        ("approval_state", "NOT_OWNER_CONTROLLED"),
        ("owner_reference", "SOMEONE-ELSE"),
        ("audit_mode", "PERSISTENT"),
        ("retention", "30_DAYS"),
        ("automatic_assignment_enabled", True),
        ("ticketing_enabled", True),
        ("paging_enabled", True),
        ("notifications_enabled", True),
        ("automatic_remediation_enabled", True),
    ],
)
def test_unsafe_or_bureaucratic_policy_drift_fails_closed(field, value):
    evaluator = IncidentWorkflowGovernance(base_dir=BASE_DIR)
    evaluator.policy[field] = value

    with pytest.raises(ValueError, match="unsafe or malformed"):
        evaluator.evaluate()


def test_intake_uses_sole_owner_without_owner_input():
    result = IncidentIntakeService(base_dir=BASE_DIR).create_intake(
        {
            "target_reference": "fw-fortigate-edge-01",
            "symptom": "Remote users cannot reach the published service",
            "affected_service": "SSL VPN",
            "affected_scope": "multiple_users",
            "availability": "unavailable",
            "affected_user_count": 12,
            "reported_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    assert result["status"] == "READY_FOR_EVIDENCE_REVIEW"
    assert result["intake"]["owner_reference"] == "MNE-BRAIN-OWNER"
    assert result["case"]["ownership"]["primary"]["team"] == "MNE-BRAIN-OWNER"
    assert result["readiness"]["owner_controlled"] is True
    assert result["workflow_governance"]["approval_state"] == "OWNER_CONTROLLED"


def test_governance_api_is_global_and_read_only():
    get_source = inspect.getsource(api_server.MNEBrainAPIHandler.do_GET)
    handler_source = inspect.getsource(
        api_server.MNEBrainAPIHandler._handle_incident_workflow_status
    )

    assert '"/api/incidents/workflow/status"' in get_source
    assert "IncidentWorkflowGovernance" in handler_source
    assert "EntityIndexBuilder" not in handler_source
    assert "target_reference" not in handler_source
    assert "write_text" not in handler_source
    assert "save" not in handler_source.casefold()


def test_sole_owner_governance_pilot_passes():
    result = run_p4_workflow_governance_pilot()

    assert result["success"] is True
    assert result["passed"] == result["total"] == 10
