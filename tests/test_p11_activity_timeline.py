"""Presentation-boundary checks for the redacted live activity timeline."""

from pathlib import Path


BASE = Path(__file__).resolve().parent.parent


def test_live_activity_panel_is_wired_to_the_redacted_stream():
    html = (BASE / "gui/index.html").read_text(encoding="utf-8")
    script = (BASE / "gui/scripts/activity.js").read_text(encoding="utf-8")

    assert 'id="activity-panel"' in html
    assert 'src="/scripts/activity.js"' in html
    assert "private model reasoning are never displayed" in html
    assert "stream-event" in script
    for event_type in (
        "turn.started", "investigation.planned", "agent.progress", "agent.plan",
        "command.started", "command.output", "command.completed", "tool.proposed",
        "tool.started", "tool.completed", "tool.approval_required", "file.change",
        "file.diff", "evidence.accepted", "answer.delta", "answer.final", "turn.completed",
        "turn.cancelled", "turn.failed",
    ):
        assert event_type in script


def test_live_activity_renderer_remains_presentation_only_and_safe():
    script = (BASE / "gui/scripts/activity.js").read_text(encoding="utf-8")

    assert "innerHTML" not in script
    assert "textContent" in script
    assert "document.cookie" not in script
    assert "localStorage" not in script
    assert "expected_approval_phrase" not in script
    assert "risk_level=" not in script
    assert "fetch(" not in script
    assert "collapseActivity()" in script
