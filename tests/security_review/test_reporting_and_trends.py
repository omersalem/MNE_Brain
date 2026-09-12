"""
Tests for Security Review Profiles, Fleet Trends & Delta Analytics,
and Executive/Technical Reporting Exports (HTML, PDF, JSON, CSV).
"""

from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import pytest

from core.connectors.security.models import (
    Incident,
    SeverityLevel,
    ThreatCategory,
    CollectorResult,
    CollectorStatus,
)
from core.security_review.config import SecurityAgentConfig
from core.security_review.incidents import IncidentRecord, IncidentStore
from core.security_review.reporter import SecurityReporter
from core.security_review.run_store import SecurityReviewRunStore
from core.security_review.trends import categorize_run_incidents_delta, get_trend_analytics


# --- 1. Review Profiles Tests ---

def test_default_profiles_and_migration(tmp_path):
    config_path = tmp_path / "config.json"
    # Create empty/legacy config without profiles
    config_path.write_text(json.dumps({"schedule_time": "08:00"}), encoding="utf-8")

    cfg = SecurityAgentConfig(config_path=str(config_path))
    profiles = cfg.get_profiles()
    assert len(profiles) >= 5
    profile_ids = [p["profile_id"] for p in profiles]
    assert "daily-full-review" in profile_ids
    assert "quick-perimeter-check" in profile_ids
    assert "identity-investigation" in profile_ids
    assert "email-threat-review" in profile_ids
    assert "branch-investigation" in profile_ids
    assert cfg.load().get("active_profile") == "Daily Full Review"


def test_profiles_crud(tmp_path):
    config_path = tmp_path / "config.json"
    cfg = SecurityAgentConfig(config_path=str(config_path))

    # Create new custom profile
    custom = {
        "profile_id": "custom-audit",
        "name": "Custom Perimeter Audit",
        "description": "Focused scan on core perimeter",
        "is_builtin": False,
        "options": {
            "selected_collectors": ["fortigate", "f5"],
            "time_window": {"mode": "HOURS", "hours": 12},
            "ai_engine": "CODEX",
        },
    }
    cfg.save_profile(custom)

    retrieved = cfg.get_profile("custom-audit")
    assert retrieved is not None
    assert retrieved["name"] == "Custom Perimeter Audit"
    assert retrieved["options"]["selected_collectors"] == ["fortigate", "f5"]

    # Set active profile
    active = cfg.set_active_profile("custom-audit")
    assert active["name"] == "Custom Perimeter Audit"
    assert cfg.load()["active_profile"] == "Custom Perimeter Audit"

    # Delete profile
    assert cfg.delete_profile("custom-audit") is True
    assert cfg.get_profile("custom-audit") is None


# --- 2. Delta Categorization Tests ---

def test_categorize_run_incidents_delta(tmp_path):
    run_store = SecurityReviewRunStore(tmp_path / "runs")
    now = datetime.now(timezone.utc)

    # Prior run incidents
    prior_rec = {
        "fingerprint": "fp-rec",
        "title": "Recurring Threat",
        "current_severity": "MEDIUM",
    }
    prior_esc = {
        "fingerprint": "fp-esc",
        "title": "Escalated Threat",
        "current_severity": "MEDIUM",
    }
    prior_deesc = {
        "fingerprint": "fp-deesc",
        "title": "De-escalated Threat",
        "current_severity": "HIGH",
    }
    prior_vanished = {
        "fingerprint": "fp-gone",
        "title": "Resolved Threat",
        "current_severity": "HIGH",
    }

    run_store.save_run({
        "run_id": "run-prior",
        "created_at": (now - timedelta(days=2)).isoformat(),
        "state": "COMPLETED",
    })
    run_store.save_incidents("run-prior", [prior_rec, prior_esc, prior_deesc, prior_vanished])

    # Current run incidents
    curr_new = {
        "fingerprint": "fp-new",
        "title": "Brand New Threat",
        "current_severity": "HIGH",
    }
    curr_recurring = {
        "fingerprint": "fp-rec",
        "title": "Recurring Threat",
        "current_severity": "MEDIUM",
    }
    curr_increased = {
        "fingerprint": "fp-esc",
        "title": "Escalated Threat",
        "current_severity": "CRITICAL",
    }
    curr_decreased = {
        "fingerprint": "fp-deesc",
        "title": "De-escalated Threat",
        "current_severity": "LOW",
    }

    run_store.save_run({
        "run_id": "run-curr",
        "created_at": (now - timedelta(days=1)).isoformat(),
        "state": "COMPLETED",
    })
    run_store.save_incidents("run-curr", [curr_new, curr_recurring, curr_increased, curr_decreased])

    delta = categorize_run_incidents_delta("run-curr", run_store)

    assert len(delta["new_incidents"]) == 1
    assert delta["new_incidents"][0]["fingerprint"] == "fp-new"

    assert len(delta["recurring_incidents"]) == 3  # recurring, increased, decreased are persisting

    assert len(delta["increased_severity"]) == 1
    assert delta["increased_severity"][0]["fingerprint"] == "fp-esc"

    assert len(delta["decreased_severity"]) == 1
    assert delta["decreased_severity"][0]["fingerprint"] == "fp-deesc"

    assert len(delta["no_longer_observed"]) == 1
    assert delta["no_longer_observed"][0]["fingerprint"] == "fp-gone"


# --- 3. Fleet Trend Analytics Tests ---

def test_get_trend_analytics(tmp_path):
    run_store = SecurityReviewRunStore(tmp_path / "runs")
    now = datetime.now(timezone.utc)

    # Persist 2 mock runs
    run1 = {
        "run_id": "run-001",
        "created_at": (now - timedelta(days=2)).isoformat(),
        "state": "COMPLETED",
        "incident_counts": {"CRITICAL": 1, "HIGH": 2},
    }
    run2 = {
        "run_id": "run-002",
        "created_at": (now - timedelta(days=1)).isoformat(),
        "state": "COMPLETED",
        "incident_counts": {"HIGH": 1, "MEDIUM": 1},
    }

    run_store.save_run(run1)
    run_store.save_run(run2)

    run_store.save_collector_diagnostics("run-001", [
        {"collector": "fortigate_core", "status": "SUCCESS", "duration_seconds": 1.2, "events_collected": 10},
        {"collector": "f5_bigip", "status": "SUCCESS", "duration_seconds": 0.8, "events_collected": 5},
    ])
    run_store.save_collector_diagnostics("run-002", [
        {"collector": "fortigate_core", "status": "SUCCESS", "duration_seconds": 1.1, "events_collected": 8},
        {"collector": "f5_bigip", "status": "PARTIAL", "duration_seconds": 2.0, "events_collected": 0, "error_message": "Timeout"},
    ])

    analytics = get_trend_analytics(run_store, days=7)
    assert analytics["runs_analyzed"] == 2
    assert len(analytics["seven_day_trends"]) >= 1

    # Check collector health
    dev_trends = analytics["device_health_trends"]
    assert len(dev_trends) == 2
    forti = next(d for d in dev_trends if d["collector"] == "fortigate_core")
    assert forti["successful_runs"] == 2
    assert forti["success_rate_percent"] == 100.0

    f5 = next(d for d in dev_trends if d["collector"] == "f5_bigip")
    assert f5["successful_runs"] == 1
    assert f5["failed_runs"] == 1
    assert f5["success_rate_percent"] == 50.0


# --- 4. Report Exports Tests (Executive HTML, Technical HTML, JSON, CSV, PDF) ---

def test_executive_and_technical_report_generation(tmp_path):
    run_store = SecurityReviewRunStore(tmp_path / "runs")
    reporter = SecurityReporter()
    now = datetime.now(timezone.utc)

    run_dict = {
        "run_id": "run-test-01",
        "created_at": now.isoformat(),
        "state": "COMPLETED",
        "stage": "COMPLETED",
        "incident_counts": {"total": 1, "high": 1},
        "request": {"time_window": {"mode": "HOURS", "hours": 24}},
    }
    run_store.save_run(run_dict)

    incident = {
        "fingerprint": "fp-12345",
        "display_id": "MNE-SEC-20260909-01",
        "title": "SSL-VPN Brute Force Flood",
        "current_severity": "HIGH",
        "category": "BRUTE_FORCE",
        "source_device": "FortiGate",
        "first_seen": now.isoformat(),
        "last_seen": now.isoformat(),
        "attacker_identity": "185.220.101.5",
        "target_identity": "admin",
        "event_count": 42,
        "action_taken": "DROPPED",
        "description": "42 failed login attempts within 5 minutes.",
        "remediation_cli": ["diagnose user ban add src-ip 185.220.101.5 86400"],
        "remediation_gui": ["Block user IP on FortiGate GUI"],
        "diagnostics": {"stage_timings_ms": {"query": 120, "parse": 15}},
    }
    run_store.save_incidents("run-test-01", [incident])

    collectors = [
        {"collector": "fortigate_core", "status": "SUCCESS", "duration_seconds": 1.2, "events_collected": 42},
        {"collector": "f5_bigip", "status": "SUCCESS", "duration_seconds": 0.8, "events_collected": 0},
    ]
    run_store.save_collector_diagnostics("run-test-01", collectors)

    # Executive Report HTML
    exec_html = reporter.generate_executive_report("run-test-01", run_store)
    assert "Executive Cyber Threat & Risk Briefing" in exec_html
    assert "SSL-VPN Brute Force Flood" in exec_html

    # Technical Report HTML
    tech_html = reporter.generate_technical_report("run-test-01", run_store)
    assert "MNE Technical Security Operations Report" in tech_html
    assert "SSL-VPN Brute Force Flood" in tech_html
    assert "diagnose user ban add src-ip 185.220.101.5" in tech_html
    assert "Perimeter & Identity Log Diagnostics" in tech_html
    assert "Stage Timings" in tech_html

    # JSON Export
    json_data = reporter.generate_json_export("run-test-01", run_store)
    assert json_data["run_id"] == "run-test-01"
    assert len(json_data["incidents"]) == 1
    assert json_data["incidents"][0]["display_id"] == "MNE-SEC-20260909-01"

    # CSV Export
    csv_str = reporter.generate_csv_incident_export("run-test-01", run_store)
    assert "fingerprint,display_id,title" in csv_str
    assert "MNE-SEC-20260909-01" in csv_str
    assert "185.220.101.5" in csv_str

    # PDF Compilation from dicts
    pdf_bytes = reporter.compile_pdf_report(
        incidents=[incident],
        collectors=collectors,
    )
    assert pdf_bytes.startswith(b"%PDF-")
