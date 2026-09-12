from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.connectors.security.models import (
    CollectorResult,
    CollectorStatus,
    NormalizedSecurityEvent,
    ThreatCategory,
)
from core.security_review.cli import build_parser, run_security_pipeline
from core.security_review.config import SecurityAgentConfig
from core.security_review.daily_job import run_daily_job
from core.security_review.run_store import SecurityReviewRunStore
from core.security_review.service import SecurityReviewService


class FakeCollector:
    def __init__(self, device_name: str):
        self.device_name = device_name

    def collect_logs(self, hours_back: int = 24) -> CollectorResult:
        ev = NormalizedSecurityEvent(
            event_id=f"ev-{self.device_name}",
            timestamp=datetime.now(timezone.utc),
            source_device=self.device_name,
            category=ThreatCategory.BRUTE_FORCE,
            threat_name="Test Threat",
            attacker_ip="192.168.1.50",
            target="root",
            action_taken="BLOCKED",
        )
        return CollectorResult(
            device_name=self.device_name,
            status=CollectorStatus.SUCCESS,
            events=[ev],
            collection_duration_seconds=0.01,
        )


def test_cli_parser_options():
    parser = build_parser()
    args = parser.parse_args(["--run-now"])
    assert args.run_now is True
    assert args.dry_run is False

    args_dry = parser.parse_args(["--dry-run"])
    assert args_dry.dry_run is True

    args_rem = parser.parse_args(["--remediate", "MNE-SEC-20260906-01"])
    assert args_rem.remediate == "MNE-SEC-20260906-01"

    args_custom = parser.parse_args([
        "--engine", "ANTIGRAVITY",
        "--model", "gemini-1.5-pro",
        "--collectors", "fortigate_core,f5_bigip",
        "--hours", "6.5",
        "--max-records", "250",
        "--format", "json,html",
    ])
    assert args_custom.engine == "ANTIGRAVITY"
    assert args_custom.model == "gemini-1.5-pro"
    assert args_custom.collectors == "fortigate_core,f5_bigip"
    assert args_custom.hours == 6.5
    assert args_custom.max_records == 250
    assert args_custom.format == "json,html"


def test_run_security_pipeline_dry_run_with_fake_collectors(tmp_path):
    # Dry run should execute without calling SMTP server or live network
    store = SecurityReviewRunStore(tmp_path / "runs")
    cfg_file = tmp_path / "test_config.json"
    cfg_mgr = SecurityAgentConfig(str(cfg_file))

    fake_registry = {
        "fortigate_core": FakeCollector("FortiGate"),
        "fortianalyzer": FakeCollector("FortiAnalyzer"),
        "f5_bigip": FakeCollector("F5 BIG-IP"),
        "cisco_fmc": FakeCollector("Cisco FMC"),
        "sophos_email": FakeCollector("Sophos Email"),
        "active_directory": FakeCollector("Active Directory"),
        "exchange_2019": FakeCollector("Exchange"),
    }

    svc = SecurityReviewService(
        run_store=store,
        collector_registry=fake_registry,
        config_mgr=cfg_mgr,
    )

    result = run_security_pipeline(
        dry_run=True,
        send_email=False,
        service=svc,
        collector_registry=fake_registry,
    )

    assert result is not None
    assert result["success"] is True
    assert "html_report" in result
    assert "pdf_report" in result
    assert "incidents" in result
    assert len(result["collectors"]) == 7


def test_daily_job_execution(tmp_path):
    cfg_file = tmp_path / "test_config.json"
    cfg_mgr = SecurityAgentConfig(str(cfg_file))
    cfg_mgr.save({"schedule_enabled": True, "schedule_time": "07:00", "recipients": ["admin@mne.gov.ps"]})

    mock_pipeline = MagicMock(return_value={"success": True, "email_sent": True})
    exit_code = run_daily_job(config_mgr=cfg_mgr, pipeline_fn=mock_pipeline)

    assert exit_code == 0
    assert mock_pipeline.called


def test_run_security_pipeline_parameterized(tmp_path):
    store = SecurityReviewRunStore(tmp_path / "runs")
    cfg_file = tmp_path / "test_config.json"
    cfg_mgr = SecurityAgentConfig(str(cfg_file))

    fake_registry = {
        "fortigate_core": FakeCollector("FortiGate"),
        "f5_bigip": FakeCollector("F5 BIG-IP"),
    }

    svc = SecurityReviewService(
        run_store=store,
        collector_registry=fake_registry,
        config_mgr=cfg_mgr,
    )

    result = run_security_pipeline(
        dry_run=True,
        send_email=False,
        service=svc,
        collector_registry=fake_registry,
        engine="NONE",
        collectors="fortigate_core",
        hours=6.0,
        max_records=100,
        formats="json",
    )

    assert result is not None
    assert result["success"] is True
    assert len(result["collectors"]) == 1
    assert result["collectors"][0].device_name == "FortiGate"
