"""
Tests for MNE_Brain Windows Service Registration & Management Scripts.
"""

from pathlib import Path
import subprocess
import shutil
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
REGISTER_SCRIPT = SCRIPTS_DIR / "register_server_service.ps1"
MANAGE_SCRIPT = SCRIPTS_DIR / "manage_server_service.ps1"


@pytest.mark.offline
def test_service_scripts_exist():
    """Verify that both service management scripts exist in scripts/."""
    assert REGISTER_SCRIPT.is_file(), f"Missing {REGISTER_SCRIPT}"
    assert MANAGE_SCRIPT.is_file(), f"Missing {MANAGE_SCRIPT}"


@pytest.mark.offline
def test_register_script_content():
    """Verify critical parameters and configurations are present in register script."""
    content = REGISTER_SCRIPT.read_text(encoding="utf-8")
    assert "MNE_Brain_Server" in content
    assert "gui/server.py" in content
    assert "operations/logs" in content
    assert "server_service.log" in content
    assert "server_service_error.log" in content
    assert "8080" in content
    assert "MNE_BRAIN_CODEX_BINARY" in content
    assert "MNE_BRAIN_OPENCODE_BINARY" in content
    assert "CODEX_HOME" in content
    assert "this script will not terminate it" in content
    assert "Stop-Process" not in content


@pytest.mark.offline
def test_manage_script_content():
    """Verify critical commands and actions are present in manage script."""
    content = MANAGE_SCRIPT.read_text(encoding="utf-8")
    assert "MNE_Brain_Server" in content
    for action in ["status", "start", "stop", "restart", "logs", "uninstall"]:
        assert action in content
    assert "Restarting clears all in-memory conversations" in content


@pytest.mark.offline
def test_powershell_syntax():
    """Validate PowerShell AST syntax if powershell is available."""
    pwsh = shutil.which("powershell.exe") or shutil.which("pwsh")
    if not pwsh:
        pytest.skip("PowerShell executable not found")

    for script in [REGISTER_SCRIPT, MANAGE_SCRIPT]:
        cmd = [
            pwsh,
            "-NoProfile",
            "-Command",
            f"[System.Management.Automation.Language.Parser]::ParseFile('{script}', [ref]$null, [ref]$null)",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0, f"Syntax error in {script}: {result.stderr}"
