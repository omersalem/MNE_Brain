"""
GUI Contract tests verifying element IDs, navigation tabs, run review controls,
real-time console controls, and script loading in gui/index.html.
"""

from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = REPO_ROOT / "gui" / "index.html"
SECURITY_AGENT_JS = REPO_ROOT / "gui" / "scripts" / "security_agent.js"
PROVIDERS_JS = REPO_ROOT / "gui" / "scripts" / "providers.js"


def test_gui_script_loading():
    content = INDEX_HTML.read_text(encoding="utf-8")
    assert '<script type="module" src="/scripts/security_agent.js"></script>' in content
    assert '<script type="module" src="/scripts/providers.js"></script>' in content


def test_gui_security_dialog_and_tabs():
    content = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="security-agent-dialog"' in content
    assert 'id="security-agent-button"' in content

    # 5 Tabs
    assert 'id="sec-tab-overview"' in content
    assert 'id="sec-tab-run"' in content
    assert 'id="sec-tab-incidents"' in content
    assert 'id="sec-tab-analysis"' in content
    assert 'id="sec-tab-history"' in content

    # 5 Panels
    assert 'id="sec-panel-overview"' in content
    assert 'id="sec-panel-run"' in content
    assert 'id="sec-panel-incidents"' in content
    assert 'id="sec-panel-analysis"' in content
    assert 'id="sec-panel-history"' in content


def test_gui_overview_elements():
    content = INDEX_HTML.read_text(encoding="utf-8")
    expected_ids = [
        "sec-btn-run",
        "sec-btn-view-html",
        "sec-btn-download-pdf",
        "sec-btn-test-email",
        "sec-stat-critical",
        "sec-stat-high",
        "sec-stat-medium",
        "sec-stat-total",
        "sec-stat-devices",
        "sec-schedule-form",
        "sec-schedule-enabled",
        "sec-schedule-time",
        "sec-scheduler-badge",
        "sec-task-state",
        "sec-task-next",
        "sec-recipients-list",
        "sec-recipients-count",
        "sec-new-email",
        "sec-btn-add-email",
        "sec-btn-save-recipients",
        "sec-devices-grid",
    ]
    for el_id in expected_ids:
        assert f'id="{el_id}"' in content, f"Missing required element id='{el_id}'"


def test_gui_run_review_and_console_elements():
    content = INDEX_HTML.read_text(encoding="utf-8")
    expected_ids = [
        "sec-run-mode",
        "sec-time-preset",
        "sec-custom-time-group",
        "sec-start-time",
        "sec-end-time",
        "sec-btn-select-all-collectors",
        "sec-btn-deselect-all-collectors",
        "sec-analysis-engine",
        "sec-analysis-model",
        "sec-send-email-check",
        "sec-btn-start-review",
        "sec-console-section",
        "sec-run-console",
        "sec-run-stage",
        "sec-run-status-indicator",
        "sec-current-collector",
        "sec-elapsed-time",
        "sec-count-fetched",
        "sec-count-parsed",
        "sec-collector-duration",
        "sec-btn-cancel-run",
        "sec-btn-retry-failed",
        "sec-btn-run-again",
        "sec-btn-open-results",
    ]
    for el_id in expected_ids:
        assert f'id="{el_id}"' in content, f"Missing required element id='{el_id}'"


def test_gui_history_and_incidents_elements():
    content = INDEX_HTML.read_text(encoding="utf-8")
    expected_ids = [
        "sec-history-table",
        "sec-history-tbody",
        "sec-history-refresh-btn",
        "sec-incidents-table",
        "sec-incidents-tbody",
        "sec-incidents-search",
        "sec-incidents-filter-sev",
    ]
    for el_id in expected_ids:
        assert f'id="{el_id}"' in content, f"Missing required element id='{el_id}'"


def test_security_js_has_no_business_logic_calculations():
    content = SECURITY_AGENT_JS.read_text(encoding="utf-8")
    # Must NOT calculate risk scores or severity in JS
    assert "calculateRisk" not in content
    assert "scoreRisk" not in content
    assert "computeSeverity" not in content
