#!/usr/bin/env python3
"""Acceptance test for the non-connecting P2 live-pilot preflight."""

import sys
from pathlib import Path


base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from scripts.preflight_p2_live_pilot import run_p2_live_preflight


def test_p2_live_preflight_fails_closed() -> None:
    report = run_p2_live_preflight(base_dir)

    assert report["status"] == "BLOCKED"
    assert report["mode"] == "NON_CONNECTING_PREFLIGHT"
    assert report["profile_name"] == "fortigate_edge"
    assert report["target_entity"] == "fw-fortigate-edge-01"
    assert report["target_resolved"] is True
    assert report["credential_key"] == "FORTIGATE_CREDENTIAL_REF"
    assert report["credential_value_returned"] is False
    assert report["connection_attempted"] is False
    assert "TARGET_CONFIRMATION_MISSING" not in report["blockers"]
    assert "OWNER_PROCEED_MISSING" not in report["blockers"]
    assert "LIVE_TRANSPORT_ADAPTER_MISSING" not in report["blockers"]
    assert "LIVE_POLICY_DISABLED" in report["blockers"]
