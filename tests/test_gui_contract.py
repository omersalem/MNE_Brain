"""
GUI Contract tests verifying element IDs, navigation tabs, run review controls,
real-time console controls, and script loading in gui/index.html.
"""

from pathlib import Path
import re
import shutil
import subprocess
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = REPO_ROOT / "gui" / "index.html"
SECURITY_AGENT_JS = REPO_ROOT / "gui" / "scripts" / "security_agent.js"
PROVIDERS_JS = REPO_ROOT / "gui" / "scripts" / "providers.js"
AUTH_JS = REPO_ROOT / "gui" / "scripts" / "auth.js"
GUI_SCRIPTS_DIR = REPO_ROOT / "gui" / "scripts"


def test_gui_script_loading():
    content = INDEX_HTML.read_text(encoding="utf-8")
    assert '<script type="module" src="/scripts/security_agent.js"></script>' in content
    assert '<script type="module" src="/scripts/providers.js"></script>' in content
    assert '<script type="module" src="/scripts/preferences.js"></script>' in content
    assert '<script type="module" src="/scripts/auth.js"></script>' in content
    assert '<script type="module" src="/scripts/threads.js"></script>' in content


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


def test_provider_settings_refreshes_on_open_and_degrades_per_engine():
    content = PROVIDERS_JS.read_text(encoding="utf-8")
    assert "Promise.allSettled" in content
    assert "Refreshing provider diagnostics" in content
    assert "document.addEventListener('owner-authenticated'" in content


def test_gui_all_13_modules_exist_and_no_inner_html():
    required_modules = {
        "api.js", "auth.js", "threads.js", "composer.js",
        "streaming.js", "activity.js", "evidence.js", "tool_calls.js",
        "approvals.js", "providers.js", "p10.js", "security_agent.js", "preferences.js"
    }
    present_modules = {p.name for p in GUI_SCRIPTS_DIR.glob("*.js")}
    assert present_modules == required_modules

    for script_file in GUI_SCRIPTS_DIR.glob("*.js"):
        code = script_file.read_text(encoding="utf-8")
        assert "innerHTML" not in code, f"Forbidden innerHTML found in {script_file.name}"


def test_gui_settings_preference_controls():
    content = INDEX_HTML.read_text(encoding="utf-8")
    expected_ids = [
        "pref-theme-select",
        "pref-accent-select",
        "pref-density-select",
        "pref-font-select",
        "pref-motion-select",
        "pref-default-engine-select",
        "pref-default-model-select",
        "pref-sidebar-width",
        "pref-show-archived",
    ]
    for el_id in expected_ids:
        assert f'id="{el_id}"' in content, f"Missing required preference control id='{el_id}'"


def test_gui_no_raw_decorative_emojis_in_index_html():
    content = INDEX_HTML.read_text(encoding="utf-8")
    # Common decorative emoji ranges in Unicode
    emoji_pattern = re.compile(r"[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF\U00002702-\U000027B0]")
    matches = emoji_pattern.findall(content)
    assert not matches, f"Found decorative emojis in gui/index.html: {set(matches)}"


def test_auth_js_closes_open_dialogs_on_expiration():
    content = AUTH_JS.read_text(encoding="utf-8")
    assert "dialog[open]" in content


def test_gui_archived_banner_and_engine_warning_elements():
    content = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="pref-default-engine-warning"' in content
    assert 'id="composer-archived-banner"' in content
    assert 'id="composer-unarchive-btn"' in content


def test_gui_no_raw_decorative_emojis_in_scripts():
    emoji_pattern = re.compile(r"[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF\U00002600-\U000027BF\U00002300-\U000023FF]")
    for script_file in GUI_SCRIPTS_DIR.glob("*.js"):
        content = script_file.read_text(encoding="utf-8")
        # Exclude known user markdown attachment syntax in composer.js: 📎
        cleaned = content.replace("📎", "")
        matches = emoji_pattern.findall(cleaned)
        # Filter out standard non-emoji glyphs (e.g. checkmark ✓ U+2713)
        matches = [m for m in matches if m not in ("✓", "➔", "×", "•")]
        assert not matches, f"Found decorative emojis in {script_file.name}: {set(matches)}"


def test_gui_node_test_suite_passes():
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("node is not available on this host")
    proc = subprocess.run(
        [
            node_bin,
            "--test",
            "tests/test_gui_preferences.test.mjs",
            "tests/test_gui_engine_behavior.test.mjs",
            "tests/test_gui_archived_and_session.test.mjs",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"Node test suite failed:\n{proc.stdout}\n{proc.stderr}"
