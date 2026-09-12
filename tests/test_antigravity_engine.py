"""Acceptance and unit tests for the Antigravity CLI (1.1.26) engine and Gemini 3.8 Flash."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import pytest

from core.antigravity.harness import (
    ANTIGRAVITY_PROVIDER_ID,
    DEFAULT_ANTIGRAVITY_MODEL,
    AntigravityHarness,
    discover_agy_executable,
    query_models,
)
from core.conversation.engine import ConversationEngine
from core.conversation.thread_store import ThreadStore, ThreadStoreError
from core.tools.broker import ToolBroker


def test_antigravity_discovery_and_readiness():
    """Verify that Antigravity harness discovers agy.exe or handles missing binary safely."""
    harness = AntigravityHarness(BASE)
    readiness = harness.readiness(start_process=False)
    assert readiness["default_model"] == DEFAULT_ANTIGRAVITY_MODEL
    assert readiness["unrestricted_read"] is True
    assert readiness["write_governance"] == "RISK_AND_ROLLBACK_REVIEW_REQUIRED"
    assert "gemini-3.8-flash-high" in [m["id"] for m in readiness["models"]]

    # When binary is missing or dummy
    dummy_harness = AntigravityHarness(BASE, binary_path=Path("non_existent_agy_path_test.exe"))
    missing_readiness = dummy_harness.readiness(start_process=False)
    assert missing_readiness["status"] == "NOT_INSTALLED"
    assert len(missing_readiness["missing_prerequisites"]) > 0


def test_antigravity_models_query():
    """Verify query_models returns Gemini 3.8 Flash and associated variants."""
    models = query_models(None)
    model_ids = {m["id"] for m in models}
    assert "gemini-3.8-flash-high" in model_ids
    assert "gemini-3.8-flash-medium" in model_ids
    assert "gemini-3.8-flash-low" in model_ids
    assert "gemini-3.7-flash-high" in model_ids
    assert all("id" in m and "label" in m for m in models)


def test_antigravity_stream_event_processing():
    """Verify that NDJSON events from agy.exe are parsed into deltas, progress, and completion."""
    events_captured: list[tuple[str, str, str, dict]] = []
    completed_turns: list[tuple[str, str]] = []
    failed_turns: list[tuple[str, str]] = []

    def event_sink(thread_id, turn_id, event_type, payload):
        events_captured.append((thread_id, turn_id, event_type, payload))

    def completion_sink(turn_id, answer):
        completed_turns.append((turn_id, answer))

    def failure_sink(turn_id, error):
        failed_turns.append((turn_id, error))

    harness = AntigravityHarness(
        BASE,
        event_sink=event_sink,
        completion_sink=completion_sink,
        failure_sink=failure_sink,
        binary_path=Path("mock_agy.exe"),
    )

    ndjson_output = "\n".join([
        json.dumps({"event": "init", "conversation_id": "agy_conv_999"}),
        json.dumps({"event": "step_update", "step_update": {"step_type": "agent_response", "text_delta": "Analyzing interface "}}),
        json.dumps({"event": "step_update", "step_update": {"step_type": "agent_response", "text_delta": "counters..."}}),
        json.dumps({"event": "result", "result": {"status": "SUCCESS", "response": "Analyzing interface counters..."}}),
    ]) + "\n"

    mock_proc = MagicMock()
    mock_proc.stdout = io.StringIO(ndjson_output)
    mock_proc.stderr = io.StringIO("")
    mock_proc.poll.return_value = 0
    mock_proc.wait.return_value = 0
    mock_proc.returncode = 0

    with patch("subprocess.Popen", return_value=mock_proc):
        with patch.object(harness, "binary", return_value=Path("mock_agy.exe")):
            harness.start_turn(
                gui_thread_id="thr_test_123",
                gui_turn_id="trn_test_456",
                content="show interfaces",
                owner_session_digest="a" * 64,
                model_id="gemini-3.8-flash-high",
            )
            time.sleep(0.3)

    assert len(completed_turns) == 1
    assert completed_turns[0] == ("trn_test_456", "Analyzing interface counters...")
    delta_texts = [p["text"] for _, _, etype, p in events_captured if etype == "answer.delta"]
    assert "".join(delta_texts) == "Analyzing interface counters..."
    assert any(etype == "answer.final" and p.get("text") == "Analyzing interface counters..." for _, _, etype, p in events_captured)
    assert harness._conversations.get("thr_test_123") == "agy_conv_999"


def test_antigravity_write_risk_and_rollback_review():
    """Verify that write operations calculate risk and rollback feasibility for owner review."""
    broker = ToolBroker(BASE)
    harness = AntigravityHarness(BASE, tool_broker=broker)

    # 1. Low risk with declared automated rollback
    plan_with_rollback = harness.prepare_write_review(
        entity_id="fw-fortigate-jenin-01",
        protocol="ssh",
        operations=["config system global", "set timezone 04", "end"],
        intended_change="Set timezone",
        expected_impact="None",
        downtime_risk="None",
        blast_radius="None",
        prechecks=["get system status"],
        postchecks=["get system status"],
        rollback_steps=["config system global", "set timezone 03", "end"],
        owner_requested=True,
    )
    assert plan_with_rollback["status"] == "AWAITING_FINAL_CONFIRMATION"
    warning = plan_with_rollback["warning"]
    assert warning["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert warning["can_rollback"] is True
    assert warning["rollback_status"] == "DECLARED"
    assert "Automated rollback available" in warning["rollback_summary"]
    assert len(warning["rollback_steps"]) > 0

    # 2. Irreversible change without rollback steps
    plan_irreversible = harness.prepare_write_review(
        entity_id="fw-fortigate-jenin-01",
        protocol="ssh",
        operations=["execute formatlogdisk"],
        intended_change="Format log disk",
        expected_impact="Log data loss",
        downtime_risk="None",
        blast_radius="Disk",
        prechecks=["get system status"],
        postchecks=["get system status"],
        rollback_steps=None,
        owner_requested=True,
    )
    assert plan_irreversible["status"] == "AWAITING_FINAL_CONFIRMATION"
    warning_irrev = plan_irreversible["warning"]
    assert warning_irrev["can_rollback"] is False
    assert warning_irrev["rollback_status"] == "NO_SAFE_ROLLBACK"
    assert "IRREVERSIBLE" in warning_irrev["rollback_summary"]
    assert warning_irrev["rollback_steps"] == ["NO_SAFE_ROLLBACK"]


def test_conversation_engine_antigravity_thread_pinning():
    """Verify thread creation, provider mapping, and engine pinning for antigravity."""
    store = ThreadStore(BASE)
    thread = store.create_thread(
        title="Antigravity Gemini 3.8 Thread",
        provider_id=ANTIGRAVITY_PROVIDER_ID,
        engine_id="antigravity",
        model_id=DEFAULT_ANTIGRAVITY_MODEL,
        permission_mode="OWNER_DIRECT",
    )
    assert thread["engine_id"] == "antigravity"
    assert thread["provider_id"] == ANTIGRAVITY_PROVIDER_ID
    assert thread["model_id"] == "gemini-3.8-flash-high"

    # Switching model before any turns is allowed
    pinned = store.pin_engine(
        thread["thread_id"],
        provider_id=ANTIGRAVITY_PROVIDER_ID,
        engine_id="antigravity",
        model_id="gemini-3.8-flash-medium",
    )
    assert pinned["model_id"] == "gemini-3.8-flash-medium"

    # Adding a turn pins the engine and model
    turn = store.create_turn(thread["thread_id"])
    store.add_message(turn["turn_id"], role="user", content="ping switch")
    with pytest.raises(ThreadStoreError, match="pinned after the first turn"):
        store.pin_engine(
            thread["thread_id"],
            provider_id=ANTIGRAVITY_PROVIDER_ID,
            engine_id="antigravity",
            model_id="gemini-3.8-flash-low",
        )


def test_antigravity_dynamic_version_in_progress():
    """Verify that progress event displays the dynamic version without hard-coded text."""
    events_captured = []

    def event_sink(thread_id, turn_id, event_type, payload):
        events_captured.append((event_type, payload))

    harness = AntigravityHarness(
        BASE,
        event_sink=event_sink,
        binary_path=Path("mock_agy.exe"),
    )

    ndjson_output = "\n".join([
        json.dumps({"event": "init", "conversation_id": "conv_dyn_ver"}),
        json.dumps({"event": "result", "result": {"status": "SUCCESS", "response": "Done"}}),
    ]) + "\n"

    mock_proc = MagicMock()
    mock_proc.stdout = io.StringIO(ndjson_output)
    mock_proc.stderr = io.StringIO("")
    mock_proc.poll.return_value = 0
    mock_proc.wait.return_value = 0
    mock_proc.returncode = 0

    with patch("subprocess.Popen", return_value=mock_proc):
        with patch.object(harness, "binary", return_value=Path("mock_agy.exe")):
            with patch.object(harness, "get_version", return_value="2.0.4-preview"):
                harness.start_turn(
                    gui_thread_id="thr_dyn_1",
                    gui_turn_id="trn_dyn_1",
                    content="check version",
                    owner_session_digest="b" * 64,
                )
                time.sleep(0.3)

    progress_events = [p for etype, p in events_captured if etype == "agent.progress"]
    assert len(progress_events) == 1
    assert "2.0.4-preview" in progress_events[0]["text"]
    assert "1.1.26" not in progress_events[0]["text"]


def test_antigravity_structured_pack_support():
    """Verify that Antigravity harness incorporates structured pack when provided."""
    captured_cmds = []

    harness = AntigravityHarness(
        BASE,
        binary_path=Path("mock_agy.exe"),
    )

    ndjson_output = "\n".join([
        json.dumps({"event": "init", "conversation_id": "conv_pack_1"}),
        json.dumps({"event": "result", "result": {"status": "SUCCESS", "response": "Pack analyzed"}}),
    ]) + "\n"

    mock_proc = MagicMock()
    mock_proc.stdout = io.StringIO(ndjson_output)
    mock_proc.stderr = io.StringIO("")
    mock_proc.poll.return_value = 0
    mock_proc.wait.return_value = 0
    mock_proc.returncode = 0

    def mock_popen(cmd, **kwargs):
        captured_cmds.append(cmd)
        return mock_proc

    with patch("subprocess.Popen", side_effect=mock_popen):
        with patch.object(harness, "binary", return_value=Path("mock_agy.exe")):
            pack = {"pack_id": "pack-999", "target_type": "INCIDENT", "threat": "XSS"}
            harness.start_turn(
                gui_thread_id="thr_pack_1",
                gui_turn_id="trn_pack_1",
                content="Analyze this incident:",
                owner_session_digest="c" * 64,
                structured_pack=pack,
            )
            time.sleep(0.3)

    turn_cmds = [c for c in captured_cmds if "--model" in c]
    assert len(turn_cmds) == 1
    full_cmd_str = " ".join(turn_cmds[0])
    assert "pack-999" in full_cmd_str
    assert "INCIDENT" in full_cmd_str
