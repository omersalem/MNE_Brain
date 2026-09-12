"""
Unit tests for SecurityReviewService, SecurityReviewJobManager, SecurityReviewRunStore, and contracts.
Uses fake collectors and temporary storage to ensure no live network or infrastructure access.
"""

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pytest
import jsonschema

from core.connectors.security.models import (
    CollectorResult,
    CollectorStatus,
    NormalizedSecurityEvent,
    SeverityLevel,
    ThreatCategory,
)
from core.security_review.config import SecurityAgentConfig
from core.security_review.contracts import (
    AnalysisEngine,
    CollectorDiagnostic,
    DiagnosticStatus,
    ReportFormat,
    ReviewMode,
    RunState,
    SecurityReviewRequest,
    SecurityReviewRun,
    validate_contract,
)
from core.security_review.incidents import IncidentStore
from core.security_review.jobs import SecurityReviewJobManager
from core.security_review.run_store import SecurityReviewRunStore
from core.security_review.service import SecurityReviewService


class FakeCollector:
    """Mock collector for isolated testing."""

    def __init__(self, device_name: str, events: List[NormalizedSecurityEvent] = None, fail: bool = False, delay: float = 0.0):
        self.device_name = device_name
        self.events = events or []
        self.fail = fail
        self.delay = delay

    def collect_logs(self, hours_back: int = 24) -> CollectorResult:
        if self.delay > 0:
            time.sleep(self.delay)
        if self.fail:
            return CollectorResult(
                device_name=self.device_name,
                status=CollectorStatus.FAILED,
                error_message=f"Simulated failure on {self.device_name}",
                events=[],
                collection_duration_seconds=0.01,
            )
        return CollectorResult(
            device_name=self.device_name,
            status=CollectorStatus.SUCCESS,
            events=self.events,
            collection_duration_seconds=0.01,
        )


def _make_fake_event(event_id: str, device: str, threat: str = "Test Threat") -> NormalizedSecurityEvent:
    return NormalizedSecurityEvent(
        event_id=event_id,
        timestamp=datetime.now(timezone.utc),
        source_device=device,
        category=ThreatCategory.BRUTE_FORCE,
        threat_name=threat,
        attacker_ip="192.168.1.100",
        target="admin",
        action_taken="BLOCKED",
    )


def test_contracts_schema_validation():
    req = SecurityReviewRequest(
        mode=ReviewMode.QUICK,
        collector_ids=["fortigate_core", "f5_bigip"],
        hours_back=12.0,
        analysis_engine=AnalysisEngine.NONE,
        send_email=False,
        report_formats=[ReportFormat.HTML, ReportFormat.JSON],
    )
    req.validate()

    diag = CollectorDiagnostic(
        collector_id="fortigate_core",
        canonical_entity="fortigate_core",
        status=DiagnosticStatus.SUCCESS,
        diagnostic_code="OK",
        message="Collected 10 events",
    )
    diag.validate()

    run = SecurityReviewRun(
        run_id="sec-run-test-01",
        request=req.to_dict(),
        state=RunState.QUEUED,
        stage="INITIALIZED",
    )
    run.validate()


def test_contracts_schema_invalid_request():
    invalid_data = {
        "mode": "INVALID_MODE",
        "collector_ids": [],
        "analysis_engine": "NONE",
        "send_email": False,
        "report_formats": ["HTML"],
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_contract(invalid_data, "security-review-request.schema.json")


def test_run_store_persistence(tmp_path):
    store = SecurityReviewRunStore(tmp_path)
    run = SecurityReviewRun(
        run_id="sec-run-persist-01",
        request={"mode": "FULL", "collector_ids": ["fortigate_core"], "analysis_engine": "NONE", "send_email": False, "report_formats": ["HTML"], "hours_back": 24},
        state=RunState.RUNNING,
        stage="COLLECTION",
    )
    store.save_run(run)

    loaded = store.get_run("sec-run-persist-01")
    assert loaded is not None
    assert loaded["run_id"] == "sec-run-persist-01"
    assert loaded["state"] == "RUNNING"

    store.save_events("sec-run-persist-01", [{"event_id": "e1"}])
    assert len(store.get_events("sec-run-persist-01")) == 1

    store.save_incidents("sec-run-persist-01", [{"incident_id": "i1"}])
    assert len(store.get_incidents("sec-run-persist-01")) == 1

    report_path = store.save_report("sec-run-persist-01", "report.html", "<html>Test</html>")
    assert report_path.exists()

    runs_list = store.list_runs()
    assert len(runs_list) == 1
    assert runs_list[0]["run_id"] == "sec-run-persist-01"


def test_job_manager_background_and_events():
    jm = SecurityReviewJobManager()
    run_id = "test-job-01"

    ev1 = jm.emit_event(run_id, "test.event", {"msg": "hello"})
    assert ev1["id"] == "1"

    events = jm.get_events(run_id)
    assert len(events) == 1
    assert events[0]["event"] == "test.event"

    q, missed = jm.subscribe(run_id)
    assert len(missed) == 1

    ev2 = jm.emit_event(run_id, "test.event2", {"msg": "world"})
    queued_ev = q.get_nowait()
    assert queued_ev["event"] == "test.event2"
    jm.unsubscribe(run_id, q)


def test_service_successful_run(tmp_path):
    store = SecurityReviewRunStore(tmp_path / "runs")
    jm = SecurityReviewJobManager()

    fake_registry = {
        "fortigate_core": FakeCollector("FortiGate", [_make_fake_event("fg-1", "FortiGate")]),
        "f5_bigip": FakeCollector("F5 BIG-IP", [_make_fake_event("f5-1", "F5 BIG-IP")]),
    }

    svc = SecurityReviewService(
        run_store=store,
        job_manager=jm,
        collector_registry=fake_registry,
    )

    req = SecurityReviewRequest(
        mode=ReviewMode.QUICK,
        collector_ids=["fortigate_core", "f5_bigip"],
        hours_back=1.0,
        analysis_engine=AnalysisEngine.NONE,
        send_email=False,
        report_formats=[ReportFormat.HTML, ReportFormat.JSON, ReportFormat.CSV],
    )

    start_time = time.time()
    run = svc.start_review(req, async_run=False)
    duration = time.time() - start_time

    assert duration < 1.0  # Under 1 second with fakes
    assert run.state == RunState.COMPLETED
    assert run.stage == "COMPLETED"
    assert len(run.collector_diagnostics) == 2
    assert run.report_artifacts.get("html") is not None
    assert run.report_artifacts.get("json") is not None
    assert run.report_artifacts.get("csv") is not None

    # Check persisted files
    saved_run = store.get_run(run.run_id)
    assert saved_run["state"] == "COMPLETED"
    assert len(store.get_events(run.run_id)) == 2


def test_service_partial_run_on_collector_failure(tmp_path):
    store = SecurityReviewRunStore(tmp_path / "runs")
    jm = SecurityReviewJobManager()

    fake_registry = {
        "fortigate_core": FakeCollector("FortiGate", [_make_fake_event("fg-1", "FortiGate")]),
        "f5_bigip": FakeCollector("F5 BIG-IP", fail=True),
    }

    svc = SecurityReviewService(
        run_store=store,
        job_manager=jm,
        collector_registry=fake_registry,
    )

    req = SecurityReviewRequest(
        mode=ReviewMode.QUICK,
        collector_ids=["fortigate_core", "f5_bigip"],
        hours_back=1.0,
        send_email=False,
        report_formats=[ReportFormat.JSON],
    )

    run = svc.start_review(req, async_run=False)

    # One succeeded, one failed -> PARTIAL, NOT unconditional success
    assert run.state == RunState.PARTIAL
    assert run.collector_diagnostics["fortigate_core"]["status"] == "SUCCESS"
    assert run.collector_diagnostics["f5_bigip"]["status"] == "FAILED"


def test_service_cancellation(tmp_path):
    store = SecurityReviewRunStore(tmp_path / "runs")
    jm = SecurityReviewJobManager()

    # Collector with small delay to test cancellation
    fake_registry = {
        "fortigate_core": FakeCollector("FortiGate", [_make_fake_event("fg-1", "FortiGate")], delay=0.05),
        "f5_bigip": FakeCollector("F5 BIG-IP", [_make_fake_event("f5-1", "F5 BIG-IP")], delay=0.05),
    }

    svc = SecurityReviewService(
        run_store=store,
        job_manager=jm,
        collector_registry=fake_registry,
    )

    req = SecurityReviewRequest(
        mode=ReviewMode.QUICK,
        collector_ids=["fortigate_core", "f5_bigip"],
        send_email=False,
        report_formats=[ReportFormat.JSON],
    )

    run_id = "test-cancellation-run"
    jm.request_cancel(run_id)  # Pre-cancel

    run = svc.start_review(req, run_id=run_id, async_run=False)

    assert run.state == RunState.CANCELLED
    assert run.stage == "CANCELLED"


def test_service_targeted_retry(tmp_path):
    store = SecurityReviewRunStore(tmp_path / "runs")
    jm = SecurityReviewJobManager()

    fake_registry = {
        "fortigate_core": FakeCollector("FortiGate", [_make_fake_event("fg-1", "FortiGate")]),
        "f5_bigip": FakeCollector("F5 BIG-IP", fail=True),
    }

    svc = SecurityReviewService(
        run_store=store,
        job_manager=jm,
        collector_registry=fake_registry,
    )

    req = SecurityReviewRequest(
        mode=ReviewMode.QUICK,
        collector_ids=["fortigate_core", "f5_bigip"],
        send_email=False,
        report_formats=[ReportFormat.JSON],
    )

    original_run = svc.start_review(req, async_run=False)
    assert original_run.state == RunState.PARTIAL

    # Now fix F5 and retry only failed
    fake_registry["f5_bigip"] = FakeCollector("F5 BIG-IP", [_make_fake_event("f5-fixed", "F5 BIG-IP")])

    retry_run = svc.retry_review(original_run.run_id, only_failed=True, async_run=False)
    assert retry_run.retry_of_run_id == original_run.run_id
    assert retry_run.request["collector_ids"] == ["f5_bigip"]
    assert retry_run.state == RunState.COMPLETED


def test_lazy_store_initialization(tmp_path):
    inc_dir = tmp_path / "lazy_incidents"
    run_dir = tmp_path / "lazy_runs"

    # Neither dir exists yet
    assert not inc_dir.exists()
    assert not run_dir.exists()

    inc_store = IncidentStore(inc_dir)
    assert not inc_dir.exists()
    assert inc_store.list_incidents()[1] == 0
    assert inc_store.get_incident("non-existent") is None

    run_store = SecurityReviewRunStore(run_dir)
    assert not run_dir.exists()
    assert not run_store.analyses_dir.exists()
    assert run_store.list_runs() == []
    assert run_store.list_analyses() == []
    assert run_store.get_run("non-existent") is None

    # Now saving creates the directory lazily
    run_store.save_run({"run_id": "lazy-1", "state": RunState.QUEUED.value, "stage": "INIT"})
    assert run_dir.exists()
    assert (run_dir / "lazy-1" / "run.json").exists()


def test_cancellation_persists_telemetry(tmp_path):
    store = SecurityReviewRunStore(tmp_path / "runs")
    jm = SecurityReviewJobManager()

    run_id = "cancel-telemetry-run"

    class CancellingCollector(FakeCollector):
        def collect_logs(self, *args, **kwargs):
            jm.request_cancel(run_id)
            return super().collect_logs(*args, **kwargs)

    fake_registry = {
        "fortigate_core": FakeCollector("FortiGate", [_make_fake_event("fg-1", "FortiGate")]),
        "f5_bigip": CancellingCollector("F5 BIG-IP", [_make_fake_event("f5-1", "F5 BIG-IP")]),
    }

    svc = SecurityReviewService(
        run_store=store,
        job_manager=jm,
        collector_registry=fake_registry,
    )

    req = SecurityReviewRequest(
        mode=ReviewMode.QUICK,
        collector_ids=["fortigate_core", "f5_bigip"],
        send_email=False,
        report_formats=[ReportFormat.JSON],
    )

    run = svc.start_review(req, run_id=run_id, async_run=False)
    assert run.state == RunState.CANCELLED

    # Check that collector diagnostics and events from collector 1 were persisted
    run_dir = store.get_run_dir(run_id)
    diag_file = run_dir / "collector_diagnostics.json"
    assert diag_file.exists()
    events_file = run_dir / "events.json"
    assert events_file.exists()



def test_correlation_error_handling(tmp_path, monkeypatch):
    store = SecurityReviewRunStore(tmp_path / "runs")
    fake_registry = {
        "fortigate_core": FakeCollector("FortiGate", [_make_fake_event("fg-1", "FortiGate")]),
    }

    svc = SecurityReviewService(
        run_store=store,
        collector_registry=fake_registry,
    )

    # Monkeypatch risk_engine.process_events to raise an unexpected exception
    def _fail_process_events(*args, **kwargs):
        raise RuntimeError("Simulated crash in correlation engine")

    monkeypatch.setattr(svc.risk_engine, "process_events", _fail_process_events)

    req = SecurityReviewRequest(
        mode=ReviewMode.QUICK,
        collector_ids=["fortigate_core"],
        send_email=False,
        report_formats=[ReportFormat.JSON],
    )

    run = svc.start_review(req, async_run=False)
    assert run.state == RunState.PARTIAL
    assert run.failure_summary is not None
    assert "Simulated crash in correlation engine" in run.failure_summary

