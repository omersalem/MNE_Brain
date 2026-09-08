import os
import pytest
from pathlib import Path
from core.security_review.config import SecurityAgentConfig, DEFAULT_CONFIG


def test_config_defaults(tmp_path):
    cfg_file = tmp_path / "security_agent_config.json"
    cfg = SecurityAgentConfig(config_path=str(cfg_file))
    data = cfg.load()

    assert data["schedule_time"] == "07:00"
    assert data["schedule_enabled"] is True
    assert "omersalem@mne.gov.ps" in data["recipients"]
    assert "omersalem2008@gmail.com" in data["recipients"]


def test_config_set_recipients(tmp_path):
    cfg_file = tmp_path / "security_agent_config.json"
    cfg = SecurityAgentConfig(config_path=str(cfg_file))

    # Valid update
    new_recipients = ["admin1@mne.gov.ps", "alert@mne.gov.ps"]
    updated = cfg.set_recipients(new_recipients)
    assert updated["recipients"] == new_recipients
    assert cfg.get_recipients() == new_recipients

    # Deduplication
    dups = ["user@mne.gov.ps", "USER@mne.gov.ps", "user@mne.gov.ps"]
    updated_dups = cfg.set_recipients(dups)
    assert updated_dups["recipients"] == ["user@mne.gov.ps"]

    # Invalid email rejected
    with pytest.raises(ValueError, match="Invalid email address format"):
        cfg.set_recipients(["invalid-email-address"])

    # Empty recipients rejected
    with pytest.raises(ValueError, match="At least one valid recipient"):
        cfg.set_recipients([])


def test_config_set_schedule(tmp_path, monkeypatch):
    cfg_file = tmp_path / "security_agent_config.json"
    cfg = SecurityAgentConfig(config_path=str(cfg_file))

    # Mock sync_windows_task to avoid invoking real Windows Task Scheduler during unit tests
    monkeypatch.setattr(cfg, "sync_windows_task", lambda time_str, enabled: {"synced": True, "mock": True})

    # Valid schedule
    updated = cfg.set_schedule("08:30", False)
    assert updated["schedule_time"] == "08:30"
    assert updated["schedule_enabled"] is False
    assert cfg.get_schedule_time() == "08:30"
    assert cfg.is_enabled() is False

    # Invalid schedule format rejected
    with pytest.raises(ValueError, match="Invalid schedule time"):
        cfg.set_schedule("25:99", True)

    with pytest.raises(ValueError, match="Invalid schedule time"):
        cfg.set_schedule("7am", True)


def test_config_record_run_result(tmp_path):
    cfg_file = tmp_path / "security_agent_config.json"
    cfg = SecurityAgentConfig(config_path=str(cfg_file))

    summary = {
        "success": True,
        "critical_count": 2,
        "high_count": 5,
        "medium_count": 10,
        "total_incidents": 17,
        "email_sent": True,
        "html_path": "/operations/reports/report.html",
        "pdf_path": "/operations/reports/report.pdf",
        "collectors": [
            {"device_name": "FortiGate", "status": "SUCCESS", "events_count": 50, "duration": 1.2}
        ],
    }

    cfg.record_run_result(summary)
    data = cfg.load()

    assert data["last_run"] is not None
    assert data["last_status"]["critical_count"] == 2
    assert data["last_status"]["total_incidents"] == 17
    assert data["last_status"]["email_sent"] is True


def test_config_device_catalog():
    cfg = SecurityAgentConfig()
    devices = cfg.get_device_catalog()

    assert len(devices) == 7
    names = [d["name"] for d in devices]
    assert "FortiGate Core Firewall" in names
    assert "FortiAnalyzer Central Log Analyzer" in names
    assert "F5 BIG-IP / ASM WAF" in names
    assert "Cisco Firepower Management Center (FMC)" in names
    assert "Sophos Email Protection" in names
    assert "Active Directory Domain Controller" in names
    assert "Exchange 2019 CAS/Mailbox" in names
