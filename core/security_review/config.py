"""
MNE_Brain Release 2 — Security Review Agent Configuration & Scheduler Sync
Manages persistence in `config/security_agent_config.json`, synchronizes with
Windows Task Scheduler, and coordinates recipients and schedules across GUI, CLI, and scheduled runs.
"""

import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: Dict[str, Any] = {
    "schedule_time": "07:00",
    "schedule_enabled": True,
    "recipients": [
        "omersalem@mne.gov.ps",
        "omersalem2008@gmail.com",
    ],
    "last_run": None,
    "last_status": None,
}

TASK_NAME = "MNE_Daily_Security_Review_Agent"
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class SecurityAgentConfig:
    """Manages Security Agent configuration, recipient lists, schedule parameters,
    and Windows Task Scheduler synchronization.
    """

    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            self.config_path = Path(config_path)
        else:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.config_path = base_dir / "config" / "security_agent_config.json"
        self.reports_dir = self.config_path.parent.parent / "operations" / "reports"

    def load(self) -> Dict[str, Any]:
        """Loads configuration from JSON file or creates it with defaults."""
        if not self.config_path.exists():
            self.save(DEFAULT_CONFIG)
            return dict(DEFAULT_CONFIG)
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Ensure required keys exist
            for key, val in DEFAULT_CONFIG.items():
                if key not in data:
                    data[key] = val
            return data
        except Exception as exc:
            logger.warning("Failed loading %s: %s. Using defaults.", self.config_path, exc)
            return dict(DEFAULT_CONFIG)

    def save(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Persists configuration to disk atomically."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.config_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        temp_path.replace(self.config_path)
        return config_data

    def get_recipients(self) -> List[str]:
        """Returns the list of recipient email addresses."""
        config = self.load()
        recipients = config.get("recipients", [])
        if not recipients:
            return list(DEFAULT_CONFIG["recipients"])
        return recipients

    def set_recipients(self, recipients: List[str]) -> Dict[str, Any]:
        """Validates and updates recipient email list."""
        valid_recipients = []
        for email in recipients:
            clean = str(email).strip().lower()
            if not clean:
                continue
            if not EMAIL_REGEX.match(clean):
                raise ValueError(f"Invalid email address format: '{email}'")
            if clean not in valid_recipients:
                valid_recipients.append(clean)

        if not valid_recipients:
            raise ValueError("At least one valid recipient email address is required.")

        config = self.load()
        config["recipients"] = valid_recipients
        self.save(config)
        logger.info("Updated security agent recipients: %s", valid_recipients)
        return config

    def is_enabled(self) -> bool:
        """Returns whether the scheduled automation is enabled."""
        return bool(self.load().get("schedule_enabled", True))

    def get_schedule_time(self) -> str:
        """Returns the daily trigger time (HH:MM)."""
        return str(self.load().get("schedule_time", "07:00"))

    def set_schedule(self, schedule_time: str, enabled: bool) -> Dict[str, Any]:
        """Validates schedule parameters, saves config, and syncs with Task Scheduler."""
        clean_time = schedule_time.strip()
        if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", clean_time):
            raise ValueError(f"Invalid schedule time '{schedule_time}'. Must be in 24-hour HH:MM format (e.g. 07:00).")

        # Format to HH:MM padded
        parts = clean_time.split(":")
        formatted_time = f"{int(parts[0]):02d}:{int(parts[1]):02d}"

        config = self.load()
        config["schedule_time"] = formatted_time
        config["schedule_enabled"] = bool(enabled)
        self.save(config)

        sync_result = self.sync_windows_task(formatted_time, enabled)
        config["task_scheduler_sync"] = sync_result
        return config

    def record_run_result(self, result_summary: Dict[str, Any]) -> None:
        """Records summary of the latest review run."""
        try:
            config = self.load()
            config["last_run"] = datetime.now(timezone.utc).isoformat()
            config["last_status"] = {
                "success": result_summary.get("success", True),
                "critical_count": result_summary.get("critical_count", 0),
                "high_count": result_summary.get("high_count", 0),
                "medium_count": result_summary.get("medium_count", 0),
                "total_incidents": result_summary.get("total_incidents", 0),
                "email_sent": result_summary.get("email_sent", False),
                "html_path": result_summary.get("html_path"),
                "pdf_path": result_summary.get("pdf_path"),
                "collectors": result_summary.get("collectors", []),
            }
            self.save(config)
        except Exception as exc:
            logger.warning("Failed to record run result in config: %s", exc)

    def sync_windows_task(self, schedule_time: str, enabled: bool) -> Dict[str, Any]:
        """Synchronizes Windows Task Scheduler with the specified schedule and status."""
        if sys.platform != "win32":
            return {"synced": True, "message": "Non-Windows platform; schedule stored in config only."}

        # Build PowerShell script to update or register the task
        ps_script = f"""
$ErrorActionPreference = 'Stop'
$TaskName = '{TASK_NAME}'
$WorkingDirectory = '{Path(__file__).resolve().parent.parent.parent}'
$PythonExe = '{sys.executable}'

# Check if task already exists
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($existing) {{
    $trigger = New-ScheduledTaskTrigger -Daily -At '{schedule_time}'
    Set-ScheduledTask -TaskName $TaskName -Trigger $trigger | Out-Null
    if ({' $true' if enabled else ' $false'}) {{
        Enable-ScheduledTask -TaskName $TaskName | Out-Null
    }} else {{
        Disable-ScheduledTask -TaskName $TaskName | Out-Null
    }}
    Write-Output "Task '$TaskName' updated to daily at {schedule_time} (Enabled: {enabled})."
}} else {{
    $description = "Daily cybersecurity log review, risk correlation, and HTML+PDF report dispatch for FortiGate, F5, FMC, Sophos, AD, and Exchange."
    $action = New-ScheduledTaskAction -Execute $PythonExe -Argument "-m core.security_review.daily_job" -WorkingDirectory $WorkingDirectory
    $trigger = New-ScheduledTaskTrigger -Daily -At '{schedule_time}'
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)
    Register-ScheduledTask -TaskName $TaskName -Description $description -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    if (-not ({' $true' if enabled else ' $false'})) {{
        Disable-ScheduledTask -TaskName $TaskName | Out-Null
    }}
    Write-Output "Task '$TaskName' created and set to daily at {schedule_time} (Enabled: {enabled})."
}}
"""
        try:
            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if res.returncode == 0:
                out_msg = res.stdout.strip()
                logger.info("Windows Task Scheduler synced: %s", out_msg)
                return {"synced": True, "message": out_msg}
            else:
                err_msg = res.stderr.strip() or res.stdout.strip()
                logger.warning("Windows Task Scheduler sync failed: %s", err_msg)
                return {"synced": False, "error": err_msg}
        except Exception as exc:
            logger.warning("Exception during Windows Task Scheduler sync: %s", exc)
            return {"synced": False, "error": str(exc)}

    def get_task_scheduler_status(self) -> Dict[str, Any]:
        """Queries Windows Task Scheduler for the current task status."""
        if sys.platform != "win32":
            return {"available": False, "state": "N/A (Linux/macOS)"}

        ps_cmd = f"""
$task = Get-ScheduledTask -TaskName '{TASK_NAME}' -ErrorAction SilentlyContinue
if (-not $task) {{
    Write-Output 'NOT_REGISTERED'
    exit 0
}}
$info = Get-ScheduledTaskInfo -TaskName '{TASK_NAME}' -ErrorAction SilentlyContinue
[PSCustomObject]@{{
    TaskName = $task.TaskName
    State = $task.State.ToString()
    LastRunTime = if ($info.LastRunTime) {{ $info.LastRunTime.ToString("o") }} else {{ $null }}
    NextRunTime = if ($info.NextRunTime) {{ $info.NextRunTime.ToString("o") }} else {{ $null }}
    LastTaskResult = if ($info) {{ $info.LastTaskResult }} else {{ $null }}
}} | ConvertTo-Json -Compress
"""
        try:
            res = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd], capture_output=True, text=True, timeout=10)
            output = res.stdout.strip()
            if output == "NOT_REGISTERED" or not output:
                return {"available": True, "registered": False, "state": "Not Registered"}
            data = json.loads(output)
            data["available"] = True
            data["registered"] = True
            return data
        except Exception as exc:
            logger.debug("Failed querying task scheduler: %s", exc)
            return {"available": True, "registered": False, "state": "Unknown", "error": str(exc)}

    def get_latest_reports(self) -> Dict[str, Any]:
        """Finds the latest generated HTML and PDF reports."""
        if not self.reports_dir.exists():
            return {
                "html": {"available": False, "filename": None, "path": None, "size_bytes": 0, "modified_at": None},
                "pdf": {"available": False, "filename": None, "path": None, "size_bytes": 0, "modified_at": None},
            }

        html_files = sorted(self.reports_dir.glob("MNE_Daily_Security_Report_*.html"), key=os.path.getmtime, reverse=True)
        pdf_files = sorted(self.reports_dir.glob("MNE_Daily_Security_Report_*.pdf"), key=os.path.getmtime, reverse=True)

        latest_html = html_files[0] if html_files else None
        latest_pdf = pdf_files[0] if pdf_files else None

        return {
            "html": {
                "available": latest_html is not None,
                "filename": latest_html.name if latest_html else None,
                "path": str(latest_html) if latest_html else None,
                "size_bytes": latest_html.stat().st_size if latest_html else 0,
                "modified_at": datetime.fromtimestamp(latest_html.stat().st_mtime, timezone.utc).isoformat() if latest_html else None,
            },
            "pdf": {
                "available": latest_pdf is not None,
                "filename": latest_pdf.name if latest_pdf else None,
                "path": str(latest_pdf) if latest_pdf else None,
                "size_bytes": latest_pdf.stat().st_size if latest_pdf else 0,
                "modified_at": datetime.fromtimestamp(latest_pdf.stat().st_mtime, timezone.utc).isoformat() if latest_pdf else None,
            },
        }

    def get_device_catalog(self) -> List[Dict[str, Any]]:
        """Returns the canonical catalog of the 7 monitored security appliances."""
        return [
            {
                "id": "fortigate_core",
                "name": "FortiGate Core Firewall",
                "ip": "172.23.70.4",
                "role": "Perimeter & WAN Security Gateway",
                "protocol": "SSH Disk Log Filter",
                "default_port": 22,
            },
            {
                "id": "fortianalyzer",
                "name": "FortiAnalyzer Central Log Analyzer",
                "ip": "172.23.71.206",
                "role": "Central Log Analytics, SOC Monitoring & UTM Telemetry (14 Firewalls)",
                "protocol": "SSH Log Filter / JSON-RPC",
                "default_port": 22,
            },
            {
                "id": "f5_bigip",
                "name": "F5 BIG-IP / ASM WAF",
                "ip": "172.23.70.89",
                "role": "Application Security Manager & ADC",
                "protocol": "SSH /var/log/asm & ltm",
                "default_port": 22,
            },
            {
                "id": "cisco_fmc",
                "name": "Cisco Firepower Management Center (FMC)",
                "ip": "172.23.70.77",
                "role": "Firepower Threat Defense Manager",
                "protocol": "REST API Audit Records",
                "default_port": 443,
            },
            {
                "id": "sophos_email",
                "name": "Sophos Email Protection",
                "ip": "172.23.71.39",
                "role": "Secure Email Gateway & MTA",
                "protocol": "SSH Advanced Shell smtpd_reject",
                "default_port": 22,
            },
            {
                "id": "active_directory",
                "name": "Active Directory Domain Controller",
                "ip": "172.23.71.27",
                "role": "Identity Provider & Kerberos KDC",
                "protocol": "WinRM Security EventLog (4740/4625)",
                "default_port": 5985,
            },
            {
                "id": "exchange_2019",
                "name": "Exchange 2019 CAS/Mailbox",
                "ip": "172.23.71.36",
                "role": "Messaging System & SMTP Connector",
                "protocol": "WinRM Security & Application Log",
                "default_port": 5985,
            },
        ]
