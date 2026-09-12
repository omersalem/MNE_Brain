"""
Tests for Security Review to P8/P9 Troubleshooting Bridge.
Verifies canonical resolution, scenario & binding mapping, deterministic planning,
P9 simulated live session, and incident timeline event recording.
"""

from datetime import datetime, timezone
from pathlib import Path
import pytest

from core.security_review.incidents import IncidentRecord, IncidentStore
from core.security_review.run_store import SecurityReviewRunStore
from core.security_review.troubleshooting_bridge import SecurityTroubleshootingBridge


@pytest.fixture
def bridge_env(tmp_path):
    repo_root = Path(__file__).resolve().parent.parent.parent
    run_store = SecurityReviewRunStore(tmp_path / "runs")
    inc_store = run_store.incident_store
    bridge = SecurityTroubleshootingBridge(
        base_dir=repo_root,
        run_store=run_store,
        incident_store=inc_store,
    )
    return bridge, inc_store, run_store


def test_canonical_entity_resolution_from_known_target(bridge_env):
    bridge, _, _ = bridge_env

    # Direct canonical entity match
    inc = {
        "title": "Port Scan Detected",
        "target_identity": "fw-fortigate-edge-01",
        "source_device": "FortiGate",
        "category": "INTRUSION",
    }
    canonical = bridge.resolve_canonical_entity(inc)
    assert canonical is not None
    assert canonical["entity_id"] == "fw-fortigate-edge-01"


def test_canonical_entity_resolution_from_device_fallback(bridge_env):
    bridge, _, _ = bridge_env

    # Target is generic "Perimeter", should resolve from source_device
    inc_f5 = {
        "title": "SQLi Attempt",
        "target_identity": "Perimeter",
        "source_device": "F5 BIG-IP / ASM",
        "category": "WAF_EXPLOIT",
    }
    canonical = bridge.resolve_canonical_entity(inc_f5)
    assert canonical is not None
    assert canonical["entity_id"] == "waf-f5-bigip-01"

    inc_ad = {
        "title": "Kerberos Pre-Auth Failure",
        "target_identity": "",
        "source_device": "Active Directory DC",
        "category": "BRUTE_FORCE",
    }
    canonical_ad = bridge.resolve_canonical_entity(inc_ad)
    assert canonical_ad is not None
    assert canonical_ad["entity_id"] in ("dc-windows-ad-01", "dc-mne-ad-01")


def test_scenario_and_binding_determination(bridge_env):
    bridge, _, _ = bridge_env

    # 1. VPN incident -> p8-vpn-access
    vpn_inc = {
        "title": "SSL-VPN Authentication Storm",
        "category": "BRUTE_FORCE",
        "source_device": "FortiGate",
    }
    scen, binding = bridge.determine_scenario_and_binding(vpn_inc)
    assert scen == "p8-vpn-access"
    assert binding == "p7-fortigate-edge"

    # 2. AD Lockout incident -> p8-dns-ad
    ad_inc = {
        "title": "Account Lockout Surge",
        "category": "BRUTE_FORCE",
        "source_device": "Active Directory",
    }
    scen, binding = bridge.determine_scenario_and_binding(ad_inc)
    assert scen == "p8-dns-ad"
    assert binding == "p7-ad-primary"

    # 3. Web WAF incident -> p8-web-publishing
    waf_inc = {
        "title": "WAF Command Injection Blocked",
        "category": "WAF_EXPLOIT",
        "source_device": "F5 BIG-IP",
    }
    scen, binding = bridge.determine_scenario_and_binding(waf_inc)
    assert scen == "p8-web-publishing"
    assert binding == "p7-f5"


def test_start_troubleshooting_produces_plan_and_timeline_event(bridge_env):
    bridge, inc_store, _ = bridge_env
    now = datetime.now(timezone.utc)

    # Save incident in store
    rec = IncidentRecord(
        fingerprint="inc-bridge-test-01",
        display_id="MNE-SEC-20260909-01",
        title="SSL-VPN Brute Force Flood",
        category="BRUTE_FORCE",
        signature_family="vpn-brute-force",
        source_device="FortiGate",
        attacker_identity="198.51.100.25",
        target_identity="fw-fortigate-edge-01",
        lifecycle_state="NEW",
        current_severity="HIGH",
        peak_severity="HIGH",
        first_seen=now.isoformat(),
        last_seen=now.isoformat(),
        occurrence_count=1,
        event_count=50,
    )
    inc_store.save_incident(rec)

    # Start troubleshooting (P8 planning only)
    res = bridge.start_troubleshooting(
        fingerprint="inc-bridge-test-01",
        execute_p9=False,
    )

    assert res["target_canonical"] == "fw-fortigate-edge-01"
    assert res["scenario"] == "p8-vpn-access"
    assert res["binding"] == "p7-fortigate-edge"
    assert "p8_plan" in res
    assert res["p8_plan"].get("status") in ("EVIDENCE_REQUIRED", "PLAN_READY", "EVALUATING")
    assert len(res["p8_plan"]["planned_checks"]) > 0
    assert "ai_handoff" in res
    assert "suggested_ai_prompt" in res["ai_handoff"]
    assert "fw-fortigate-edge-01" in res["ai_handoff"]["suggested_ai_prompt"]

    # Verify timeline event was recorded in IncidentStore
    timeline = inc_store.get_timeline("inc-bridge-test-01")
    handoff_events = [e for e in timeline if e.get("type") == "TROUBLESHOOTING_HANDOFF"]
    assert len(handoff_events) == 1
    assert "p8-vpn-access" in handoff_events[0]["description"]


def test_start_troubleshooting_with_simulated_p9_execution(bridge_env):
    bridge, inc_store, _ = bridge_env
    now = datetime.now(timezone.utc)

    rec = IncidentRecord(
        fingerprint="inc-bridge-test-02",
        display_id="MNE-SEC-20260909-02",
        title="DNS Amplification Threat",
        category="INTRUSION",
        signature_family="dns-anomaly",
        source_device="FortiGate",
        attacker_identity="203.0.113.88",
        target_identity="fw-fortigate-edge-01",
        lifecycle_state="NEW",
        current_severity="CRITICAL",
        peak_severity="CRITICAL",
        first_seen=now.isoformat(),
        last_seen=now.isoformat(),
        occurrence_count=1,
        event_count=100,
    )
    inc_store.save_incident(rec)

    # Mock collector for simulated P9 check execution
    def mock_collector(scenario_id: str, primary_binding: str, check_id: str, owner_proceed: bool = True):
        return {
            "status": "SUCCESS",
            "binding_id": primary_binding,
            "check_id": check_id,
            "connection_attempted": False,
            "evidence": {
                "evidence_id": f"ev-{primary_binding}-{check_id}",
                "binding_id": primary_binding,
                "check_id": check_id,
                "status": "PASS",
                "output": "System Status: NORMAL\nBanned IPs: 203.0.113.88",
            },
        }

    res = bridge.start_troubleshooting(
        fingerprint="inc-bridge-test-02",
        execute_p9=True,
        owner_proceed=True,
        collector_override=mock_collector,
    )

    assert res["p9_result"] is not None
    assert res["p9_result"]["checks_executed"] > 0
    assert len(res["p9_result"]["failed_checks"]) == 0

    # Verify both TROUBLESHOOTING_HANDOFF and TROUBLESHOOTING_EXECUTION events
    timeline = inc_store.get_timeline("inc-bridge-test-02")
    event_types = [e.get("type") for e in timeline]
    assert "TROUBLESHOOTING_HANDOFF" in event_types
    assert "TROUBLESHOOTING_EXECUTION" in event_types


def test_start_troubleshooting_nonexistent_incident_raises(bridge_env):
    bridge, _, _ = bridge_env
    with pytest.raises(ValueError, match="not found"):
        bridge.start_troubleshooting("nonexistent-fp-999")


def test_canonical_entity_unresolved_and_sophos_returns_none(bridge_env):
    bridge, _, _ = bridge_env

    # 1. Completely ambiguous device and target
    ambiguous_inc = {
        "title": "Unrecognized Telemetry Alert",
        "target_identity": "Perimeter",
        "source_device": "Unknown Vendor Switch",
        "category": "ANOMALY",
    }
    canonical = bridge.resolve_canonical_entity(ambiguous_inc)
    assert canonical is None

    # 2. Sophos device has no canonical entity (ADDITIONAL_OPERATIONAL_ASSET with null canonical_entity_id)
    sophos_inc = {
        "title": "Sophos Email Spool Surge",
        "target_identity": "Perimeter",
        "source_device": "Sophos Email Appliance",
        "category": "PHISHING",
    }
    canonical_sophos = bridge.resolve_canonical_entity(sophos_inc)
    assert canonical_sophos is None


def test_start_troubleshooting_without_collector_does_not_fabricate_evidence(bridge_env):
    bridge, inc_store, _ = bridge_env
    now = datetime.now(timezone.utc)

    rec = IncidentRecord(
        fingerprint="inc-bridge-test-no-fake",
        display_id="MNE-SEC-20260909-99",
        title="Web Exploit Inspection",
        category="WAF_EXPLOIT",
        signature_family="waf-rule",
        source_device="F5 BIG-IP",
        attacker_identity="198.51.100.55",
        target_identity="waf-f5-bigip-01",
        lifecycle_state="NEW",
        current_severity="HIGH",
        peak_severity="HIGH",
        first_seen=now.isoformat(),
        last_seen=now.isoformat(),
        occurrence_count=1,
        event_count=10,
    )
    inc_store.save_incident(rec)

    # When execute_p9=True and owner_proceed=True, but NO collector_override is supplied:
    # It must return PREPARED_NOT_EXECUTED and NOT append fake TROUBLESHOOTING_EXECUTION events
    res = bridge.start_troubleshooting(
        fingerprint="inc-bridge-test-no-fake",
        execute_p9=True,
        owner_proceed=True,
        collector_override=None,
    )

    assert res["p9_result"] is not None
    assert res["p9_result"]["status"] == "PREPARED_NOT_EXECUTED"
    assert res["p9_result"]["checks_executed"] == 0
    assert "Live P9 collector not provided" in res["p9_result"]["reason"]

    # Verify timeline ONLY has TROUBLESHOOTING_HANDOFF and NEVER has TROUBLESHOOTING_EXECUTION
    timeline = inc_store.get_timeline("inc-bridge-test-no-fake")
    event_types = [e.get("type") for e in timeline]
    assert "TROUBLESHOOTING_HANDOFF" in event_types
    assert "TROUBLESHOOTING_EXECUTION" not in event_types


def test_start_troubleshooting_unmapped_entity_fails(bridge_env):
    """Verifies that start_troubleshooting halts on unmapped canonical entities."""
    bridge, inc_store, _ = bridge_env
    now = datetime.now(timezone.utc)

    rec = IncidentRecord(
        fingerprint="inc-bridge-unknown-dev",
        display_id="MNE-SEC-20260909-00",
        title="Unknown Device Alert",
        category="INTRUSION",
        signature_family="unknown",
        source_device="alien-switch-99",
        target_identity="unregistered-iot-gateway",
        lifecycle_state="NEW",
        first_seen=now.isoformat(),
        last_seen=now.isoformat(),
    )
    inc_store.save_incident(rec)

    with pytest.raises(ValueError, match="does not resolve to an exact canonical entity"):
        bridge.start_troubleshooting(fingerprint="inc-bridge-unknown-dev")
