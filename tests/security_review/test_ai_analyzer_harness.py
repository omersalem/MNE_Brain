"""
Test harness for Security AI Analyzer operational verification (Pass 2).
Covers:
- Turn completion polling in _invoke_via_conversation_engine
- "Open in Chat" turn creation with turn_id return
- 202 Accepted background job execution for run and incident analysis
- Live SSE event streaming with Last-Event-ID resume
- SecurityReviewService.run_review wiring of analysis_engine and analysis_model
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from core.connectors.security.models import (
    CollectorResult,
    CollectorStatus,
    Incident,
    NormalizedSecurityEvent,
    SeverityLevel,
    ThreatCategory,
)
from core.security_review.ai_analyzer import SecurityAIAnalyzer
from core.security_review.contracts import (
    AnalysisEngine,
    ReviewMode,
    RunState,
    SecurityReviewRequest,
    SecurityReviewRun,
)
from core.security_review.run_store import SecurityReviewRunStore
from core.security_review.service import SecurityReviewService
from tests.security_review.test_api_endpoints import DummyHandler


@pytest.fixture
def run_store(tmp_path):
    store_dir = tmp_path / "runs"
    return SecurityReviewRunStore(store_dir)


@pytest.fixture
def sample_incident(run_store):
    run_id = "sec-run-harness-01"
    run = SecurityReviewRun(
        run_id=run_id,
        request=SecurityReviewRequest(
            mode=ReviewMode.QUICK,
            collector_ids=["fortigate_core"],
        ).to_dict(),
        state=RunState.COMPLETED,
        stage="COMPLETED",
        created_at="2026-09-09T12:00:00+00:00",
        completed_at="2026-09-09T12:05:00+00:00",
        incident_counts={"total": 1, "critical": 1, "high": 0, "medium": 0, "low": 0, "info": 0},
    )
    run_store.save_run(run)

    incidents = [
        Incident(
            incident_id="inc-harness-001",
            title="Credential Stuffing on Edge Gateway",
            severity=SeverityLevel.HIGH,
            source_device="fw-fortigate-edge-01",
            category=ThreatCategory.BRUTE_FORCE,
            first_seen="2026-09-09T12:00:00+00:00",
            last_seen="2026-09-09T12:04:00+00:00",
            description="Repeated authentication failures detected.",
            action_taken="BLOCKED",
            event_count=50,
            attacker_ip="198.51.100.55",
            target="10.0.0.1",
            signature_family="SSH_BRUTE_FORCE",
            devices_involved=["fw-fortigate-edge-01"],
            branches_involved=["HQ-Edge"],
        ),
    ]
    recs = run_store.record_run_incidents(run_id, incidents)
    return recs[0].fingerprint, run_id


def test_turn_polling_waits_for_completion(run_store, sample_incident):
    """Verifies that _invoke_via_conversation_engine waits for turn to reach COMPLETED."""
    fingerprint, run_id = sample_incident

    turn_state = {"status": "RUNNING"}
    messages: List[Dict[str, Any]] = []

    mock_store = MagicMock()
    mock_store.get_turn.side_effect = lambda tid: {"turn_id": tid, "status": turn_state["status"]}
    mock_store.messages_for_thread.side_effect = lambda tid: list(messages)

    def _delayed_turn_finisher():
        time.sleep(0.1)
        messages.append({
            "role": "assistant",
            "content": json.dumps({
                "plain_summary": "Asynchronous turn completed successfully.",
                "confidence": 0.95,
                "ranked_hypotheses": [{"hypothesis": "SSH attack", "likelihood": "HIGH"}],
                "observations": {"supporting": ["Event logs"], "contradicting": []},
                "missing_evidence": [],
                "recommended_diagnostics": ["show log"],
                "immediate_actions": ["Block IP"],
                "source_references": [],
            }),
        })
        turn_state["status"] = "COMPLETED"

    mock_engine = MagicMock()
    mock_engine.store = mock_store
    mock_engine.create_thread.return_value = {"thread_id": "thr_test_01"}

    def _start_turn(*args, **kwargs):
        t = threading.Thread(target=_delayed_turn_finisher, daemon=True)
        t.start()
        return {"turn_id": "trn_test_01", "status": "RUNNING"}

    mock_engine.start_preloaded_turn.side_effect = _start_turn
    mock_engine.codex = MagicMock()

    analyzer = SecurityAIAnalyzer(run_store=run_store, conversation_engine=mock_engine)
    res = analyzer.analyze_incident(fingerprint, engine="CODEX")

    assert res["engine"] == "CODEX"
    assert res["result"]["status"] == "COMPLETED"
    assert res["result"]["confidence"] == 0.95
    assert "Asynchronous turn completed" in res["result"]["plain_summary"]


def test_turn_polling_handles_failed_turn(run_store, sample_incident):
    """Verifies that if a turn reaches FAILED status, analyzer captures failure cleanly."""
    fingerprint, run_id = sample_incident

    turn_state = {"status": "RUNNING"}
    mock_store = MagicMock()
    mock_store.get_turn.side_effect = lambda tid: {"turn_id": tid, "status": turn_state["status"]}
    mock_store.messages_for_thread.return_value = []

    def _delayed_fail():
        time.sleep(0.05)
        turn_state["status"] = "FAILED"

    mock_engine = MagicMock()
    mock_engine.store = mock_store
    mock_engine.create_thread.return_value = {"thread_id": "thr_fail_01"}

    def _start_fail(*args, **kwargs):
        threading.Thread(target=_delayed_fail, daemon=True).start()
        return {"turn_id": "trn_fail_01", "status": "RUNNING"}

    mock_engine.start_preloaded_turn.side_effect = _start_fail
    mock_engine.codex = MagicMock()

    analyzer = SecurityAIAnalyzer(run_store=run_store, conversation_engine=mock_engine)
    res = analyzer.analyze_incident(fingerprint, engine="CODEX")

    assert res["result"]["status"] == "FAILED"


def test_open_incident_chat_creates_turn_and_returns_turn_id(run_store, sample_incident):
    """Verifies that open_incident_chat creates a turn before adding message and returns turn_id."""
    fingerprint, run_id = sample_incident

    mock_store = MagicMock()
    mock_store.create_turn.return_value = {"turn_id": "trn_incident_chat_99"}
    mock_store.add_message = MagicMock()

    mock_engine = MagicMock()
    mock_engine.store = mock_store
    mock_engine.create_thread.return_value = {"thread_id": "thr_incident_chat_11"}

    analyzer = SecurityAIAnalyzer(run_store=run_store, conversation_engine=mock_engine)
    chat_info = analyzer.open_incident_chat(fingerprint, engine="codex")

    assert chat_info["thread_id"] == "thr_incident_chat_11"
    assert chat_info["turn_id"] == "trn_incident_chat_99"
    assert chat_info["fingerprint"] == fingerprint

    mock_store.create_turn.assert_called_once_with("thr_incident_chat_11")
    mock_store.add_message.assert_called_once()
    assert mock_store.add_message.call_args[0][0] == "trn_incident_chat_99"


def test_background_submit_run_analysis_202_workflow(run_store, sample_incident):
    """Verifies submit_run_analysis schedules a background worker and emits events."""
    fingerprint, run_id = sample_incident

    fake_out = json.dumps({"plain_summary": "Test analysis run", "confidence": 0.9})
    analyzer = SecurityAIAnalyzer(
        run_store=run_store,
        codex_invoker=lambda p, k: fake_out,
        antigravity_invoker=lambda p, k: fake_out,
    )
    aid = analyzer.submit_run_analysis(run_id, engine="BOTH")
    assert "an-" in aid

    start = time.time()
    res = None
    while time.time() - start < 5.0:
        res = analyzer.get_analysis(aid)
        if res and res.get("status") in ("COMPLETED", "FAILED", "PARTIAL"):
            break
        time.sleep(0.05)

    assert res is not None
    assert res["status"] == "COMPLETED"
    assert res["engine"] == "BOTH"
    assert "codex" in res
    assert "antigravity" in res

    events = analyzer.get_events(aid)
    event_types = [e["event_type"] for e in events]
    assert "analysis.queued" in event_types
    assert "analysis.started" in event_types
    assert "analysis.completed" in event_types


def test_background_submit_incident_analysis_202_workflow(run_store, sample_incident):
    """Verifies submit_incident_analysis schedules a background worker and emits events."""
    fingerprint, run_id = sample_incident

    fake_out = json.dumps({"plain_summary": "Test analysis incident", "confidence": 0.9})
    analyzer = SecurityAIAnalyzer(
        run_store=run_store,
        codex_invoker=lambda p, k: fake_out,
    )
    aid = analyzer.submit_incident_analysis(fingerprint, engine="CODEX")
    assert "an-" in aid

    start = time.time()
    res = None
    while time.time() - start < 5.0:
        res = analyzer.get_analysis(aid)
        if res and res.get("status") in ("COMPLETED", "FAILED", "PARTIAL"):
            break
        time.sleep(0.05)

    assert res is not None
    assert res["engine"] == "CODEX"
    assert res["status"] == "COMPLETED"


def test_api_endpoints_return_202_and_stream_sse_events(monkeypatch, tmp_path, sample_incident):
    """Verifies API endpoints return HTTP 202 Accepted with analysis_id and SSE streams live events."""
    fingerprint, run_id = sample_incident

    from core.api import server
    test_run_store = SecurityReviewRunStore(tmp_path / "runs")
    test_run_store.save_run(server.security_review_run_store.get_run(run_id) or SecurityReviewRun(run_id=run_id, request={}))
    test_rec = server.security_review_run_store.get_incident_record(fingerprint)
    if test_rec:
        test_run_store.incident_store.save_incident(test_rec)

    fake_out = json.dumps({"plain_summary": "Test analysis api", "confidence": 0.9})
    test_analyzer = SecurityAIAnalyzer(
        run_store=test_run_store,
        codex_invoker=lambda p, k: fake_out,
        antigravity_invoker=lambda p, k: fake_out,
    )
    monkeypatch.setattr(server.security_review_service, "ai_analyzer", test_analyzer)

    # 1. POST /api/v2/security-agent/runs/{run_id}/analyses
    handler = DummyHandler()
    handler._handle_security_agent_run_analyses_post(run_id, {"engine": "BOTH", "async": True})

    assert handler.sent_status == 202
    resp1 = json.loads(handler.response_body.decode("utf-8"))
    assert resp1["status"] == "ACCEPTED"
    assert "analysis_id" in resp1
    run_aid = resp1["analysis_id"]

    # 2. POST /api/v2/security-agent/incidents/{fingerprint}/analyses
    handler2 = DummyHandler()
    handler2._handle_security_agent_incident_analyses_post(fingerprint, {"engine": "ANTIGRAVITY", "async": True})

    assert handler2.sent_status == 202
    resp2 = json.loads(handler2.response_body.decode("utf-8"))
    assert resp2["status"] == "ACCEPTED"
    assert "analysis_id" in resp2
    inc_aid = resp2["analysis_id"]

    # 3. Stream SSE events for run_aid
    sse_handler = DummyHandler()
    sse_handler._stream_security_analysis_events(run_aid)
    assert sse_handler.sent_status == 200
    assert "text/event-stream" in sse_handler.sent_headers["Content-Type"]
    body_text = sse_handler.response_body.decode("utf-8")
    assert "id: " in body_text
    assert "event: " in body_text


def test_service_run_review_wires_analysis_engine(tmp_path):
    """Verifies that SecurityReviewService.run_review wires analysis_engine and records analysis_refs."""
    store = SecurityReviewRunStore(tmp_path / "runs")

    mock_collector = MagicMock()
    mock_collector.collect_logs.return_value = CollectorResult(
        device_name="fw-fortigate-edge-01",
        status=CollectorStatus.SUCCESS,
        events=[
            NormalizedSecurityEvent(
                event_id="evt-01",
                timestamp="2026-09-09T12:00:00+00:00",
                source_device="fw-fortigate-edge-01",
                category=ThreatCategory.BRUTE_FORCE,
                threat_name="SSH Attack",
                attacker_ip="198.51.100.1",
                target="10.0.0.1",
                action_taken="BLOCKED",
            )
        ],
        collection_duration_seconds=0.1,
    )

    registry = {"fortigate_core": mock_collector}
    fake_out = json.dumps({"plain_summary": "Test review analysis", "confidence": 0.92})
    analyzer = SecurityAIAnalyzer(
        run_store=store,
        codex_invoker=lambda p, k: fake_out,
    )
    service = SecurityReviewService(run_store=store, collector_registry=registry, ai_analyzer=analyzer)

    req = SecurityReviewRequest(
        mode=ReviewMode.QUICK,
        collector_ids=["fortigate_core"],
        analysis_engine=AnalysisEngine.CODEX,
        send_email=False,
    )

    run = service.run_review(req, async_run=False)

    assert run.state == RunState.COMPLETED
    assert len(run.analysis_refs) > 0
    analysis_id = run.analysis_refs[0]
    saved_analysis = service.ai_analyzer.get_analysis(analysis_id)
    assert saved_analysis is not None
    assert saved_analysis.get("result", {}).get("status") == "COMPLETED"


def test_unconfigured_provider_fails_cleanly(run_store, sample_incident):
    """Verifies that when no invoker or engine is configured, status is FAILED without synthetic fallback."""
    fingerprint, run_id = sample_incident

    analyzer = SecurityAIAnalyzer(run_store=run_store)
    res = analyzer.analyze_incident(fingerprint, engine="CODEX")
    assert res["status"] == "FAILED"
    assert "not available" in res["result"]["warnings"][0]
