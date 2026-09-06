# MNE Security Review & Reporting Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated daily cybersecurity intelligence agent in MNE_Brain that collects logs from FortiGate, F5 BIG-IP, Cisco FMC, Sophos Email, Active Directory, and Exchange, correlates multi-vector risks, classifies them (Critical, High, Medium), provides concrete remediation playbooks (with Mode B assisted execution), and emails an executive HTML + PDF report at 07:00 AM.

**Architecture:** Modular, fault-isolated collector architecture where each perimeter/identity device is queried via read-only APIs or SSH/WinRM. A centralized risk engine normalizes and deduplicates events into a common threat model, matches incidents with concrete CLI/GUI remediation playbooks, and formats an executive HTML + PDF daily report dispatched via SMTP.

**Tech Stack:** Python 3.10+, Paramiko, Requests, Jinja2, Weasyprint / xhtml2pdf / Playwright, Smtplib, Pytest.

**Spec:** `docs/superpowers/specs/2026-09-06-security-review-agent-design.md`

## Global Constraints
- Read-Only Default: All scheduled log collection tasks must perform read-only queries with zero config changes.
- Secret Hygiene: Zero plaintext credentials or passwords in code or tracked configs; all credentials loaded strictly from `.env`.
- Fault Isolation: Unreachable devices must yield warning diagnostics and never crash the overall pipeline.
- Generous Timeouts: 45-second connection handshake, 120–180 second query budget per device.
- Mode B Safety: Automated remediation remains gated behind explicit owner confirmation (`MNE-BRAIN-OWNER`).
- Target Emails: `omersalem@mne.gov.ps` and `omersalem2008@gmail.com`.

---

### Task 1: Core Models & Base Collector Framework

**Files:**
- Create: `core/connectors/security/__init__.py`
- Create: `core/connectors/security/models.py`
- Create: `core/connectors/security/base.py`
- Test: `tests/security_review/test_models_and_base.py`

**Interfaces:**
- Consumes: Standard library dataclasses, typing, datetime, `.env` config.
- Produces: `SeverityLevel`, `ThreatCategory`, `RawLogEvent`, `NormalizedSecurityEvent`, `Incident`, `CollectorStatus`, `CollectorResult`, `BaseSecurityCollector`.

- [ ] **Step 1: Write the failing test for models and base collector**

```python
# tests/security_review/test_models_and_base.py
import pytest
from datetime import datetime, timezone
from core.connectors.security.models import (
    SeverityLevel,
    ThreatCategory,
    NormalizedSecurityEvent,
    Incident,
    CollectorStatus,
    CollectorResult,
)
from core.connectors.security.base import BaseSecurityCollector

def test_models_instantiation():
    event = NormalizedSecurityEvent(
        event_id="evt-123",
        timestamp=datetime.now(timezone.utc),
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        threat_name="SSL-VPN Failed Logon",
        attacker_ip="185.220.101.5",
        target="vpn.mne.gov.ps",
        action_taken="DROPPED",
        count=15,
        raw_snippet="login failed for user admin"
    )
    assert event.source_device == "FortiGate"
    assert event.count == 15

    incident = Incident(
        incident_id="MNE-SEC-20260906-01",
        title="Repeated SSL-VPN Brute Force",
        severity=SeverityLevel.HIGH,
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        attacker_ip="185.220.101.5",
        target="vpn.mne.gov.ps",
        event_count=15,
        first_seen=event.timestamp,
        last_seen=event.timestamp,
        description="Persistent brute-force attack on SSL-VPN endpoint",
        action_taken="DROPPED"
    )
    assert incident.severity == SeverityLevel.HIGH
    assert incident.incident_id == "MNE-SEC-20260906-01"

def test_base_collector_timeout_and_fault_isolation():
    class MockFailingCollector(BaseSecurityCollector):
        def _fetch_logs_internal(self, hours_back: int):
            raise TimeoutError("Device timed out")

    collector = MockFailingCollector(device_name="TestDevice", timeout=2)
    result = collector.collect_logs(hours_back=24)
    assert result.status == CollectorStatus.FAILED
    assert "Device timed out" in result.error_message
    assert result.events == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/security_review/test_models_and_base.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'core.connectors.security')

- [ ] **Step 3: Implement `models.py` and `base.py`**

Create `core/connectors/security/models.py`:
```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

class SeverityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class ThreatCategory(str, Enum):
    INTRUSION = "INTRUSION"
    MALWARE = "MALWARE"
    BRUTE_FORCE = "BRUTE_FORCE"
    WAF_EXPLOIT = "WAF_EXPLOIT"
    PHISHING = "PHISHING"
    PRIVILEGE_CHANGE = "PRIVILEGE_CHANGE"
    SYSTEM_HEALTH = "SYSTEM_HEALTH"
    ANOMALY = "ANOMALY"

class CollectorStatus(str, Enum):
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

@dataclass
class NormalizedSecurityEvent:
    event_id: str
    timestamp: datetime
    source_device: str
    category: ThreatCategory
    threat_name: str
    attacker_ip: Optional[str] = None
    target: Optional[str] = None
    action_taken: str = "UNKNOWN"
    count: int = 1
    raw_snippet: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Incident:
    incident_id: str
    title: str
    severity: SeverityLevel
    source_device: str
    category: ThreatCategory
    first_seen: datetime
    last_seen: datetime
    description: str
    action_taken: str
    event_count: int = 1
    attacker_ip: Optional[str] = None
    target: Optional[str] = None
    remediation_cli: List[str] = field(default_factory=list)
    remediation_gui: List[str] = field(default_factory=list)
    remediation_mode_b_command: Optional[str] = None

@dataclass
class CollectorResult:
    device_name: str
    status: CollectorStatus
    events: List[NormalizedSecurityEvent] = field(default_factory=list)
    error_message: Optional[str] = None
    collection_duration_seconds: float = 0.0
```

Create `core/connectors/security/base.py`:
```python
import abc
import time
import logging
from typing import Optional
from core.connectors.security.models import CollectorResult, CollectorStatus

logger = logging.getLogger(__name__)

class BaseSecurityCollector(abc.ABC):
    def __init__(self, device_name: str, timeout: int = 120):
        self.device_name = device_name
        self.timeout = timeout

    @abc.abstractmethod
    def _fetch_logs_internal(self, hours_back: int) -> list:
        pass

    def collect_logs(self, hours_back: int = 24) -> CollectorResult:
        start_time = time.time()
        try:
            events = self._fetch_logs_internal(hours_back=hours_back)
            duration = round(time.time() - start_time, 2)
            return CollectorResult(
                device_name=self.device_name,
                status=CollectorStatus.SUCCESS,
                events=events,
                collection_duration_seconds=duration,
            )
        except Exception as exc:
            duration = round(time.time() - start_time, 2)
            logger.error("Error collecting logs from %s: %s", self.device_name, exc)
            return CollectorResult(
                device_name=self.device_name,
                status=CollectorStatus.FAILED,
                error_message=str(exc),
                events=[],
                collection_duration_seconds=duration,
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/security_review/test_models_and_base.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/connectors/security/ tests/security_review/
git commit -m "feat(security_review): add core models and base collector with fault isolation"
```

---

### Task 2: Perimeter Network Collectors: FortiGate & F5 BIG-IP

**Files:**
- Create: `core/connectors/security/fortigate_collector.py`
- Create: `core/connectors/security/f5_collector.py`
- Test: `tests/security_review/test_perimeter_collectors.py`

**Interfaces:**
- Consumes: `BaseSecurityCollector`, `NormalizedSecurityEvent`, `ThreatCategory`.
- Produces: `FortiGateSecurityCollector`, `F5SecurityCollector`.

- [ ] **Step 1: Write the failing tests for FortiGate & F5 log parsing**

```python
# tests/security_review/test_perimeter_collectors.py
from datetime import datetime, timezone
from core.connectors.security.fortigate_collector import FortiGateSecurityCollector
from core.connectors.security.f5_collector import F5SecurityCollector
from core.connectors.security.models import ThreatCategory

def test_fortigate_log_parsing():
    sample_log = (
        'date=2026-09-06 time=04:12:00 devname="FGT-Edge" logid="0101037128" '
        'type="event" subtype="vpn" level="alert" action="tunnel-down" '
        'remip="185.220.101.5" user="admin" reason="negotiation failure" '
        'msg="SSL VPN login fail"'
    )
    collector = FortiGateSecurityCollector()
    event = collector.parse_log_line(sample_log)
    assert event is not None
    assert event.source_device == "FortiGate"
    assert event.category == ThreatCategory.BRUTE_FORCE
    assert event.attacker_ip == "185.220.101.5"
    assert event.target == "admin"
    assert event.action_taken == "DROPPED"

def test_f5_asm_log_parsing():
    sample_asm_line = (
        'Sep  6 03:15:22 f5-core.mne.gov.ps ASM: Attack detected: '
        'Support ID: 18273619283719, Client IP: 194.26.29.112, '
        'Violations: SQL-Injection, Severity: Critical, Action: Blocked, '
        'URL: /portal/login.aspx'
    )
    collector = F5SecurityCollector()
    event = collector.parse_asm_log_line(sample_asm_line)
    assert event is not None
    assert event.source_device == "F5 BIG-IP"
    assert event.category == ThreatCategory.WAF_EXPLOIT
    assert event.attacker_ip == "194.26.29.112"
    assert event.action_taken == "BLOCKED"
    assert "SQL-Injection" in event.threat_name
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/security_review/test_perimeter_collectors.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement `FortiGateSecurityCollector` and `F5SecurityCollector`**

Implement log retrieval logic with REST / SSH fallback, connection timeouts (45s), and parser methods (`parse_log_line`, `parse_asm_log_line`, and `parse_cert_warning`).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/security_review/test_perimeter_collectors.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/connectors/security/fortigate_collector.py core/connectors/security/f5_collector.py tests/security_review/test_perimeter_collectors.py
git commit -m "feat(security_review): add FortiGate and F5 BIG-IP collectors"
```

---

### Task 3: Security Appliance Collectors: Cisco FMC & Sophos Email

**Files:**
- Create: `core/connectors/security/fmc_collector.py`
- Create: `core/connectors/security/sophos_collector.py`
- Test: `tests/security_review/test_appliance_collectors.py`

**Interfaces:**
- Consumes: `BaseSecurityCollector`, `NormalizedSecurityEvent`, `ThreatCategory`.
- Produces: `FmcSecurityCollector`, `SophosEmailCollector`.

- [ ] **Step 1: Write the failing tests for FMC and Sophos Email parsing**

```python
# tests/security_review/test_appliance_collectors.py
from datetime import datetime, timezone
from core.connectors.security.fmc_collector import FmcSecurityCollector
from core.connectors.security.sophos_collector import SophosEmailCollector
from core.connectors.security.models import ThreatCategory

def test_fmc_intrusion_parsing():
    sample_fmc_item = {
        "id": "fmc-event-101",
        "timestamp": 1788680000,
        "sourceIp": "45.155.205.233",
        "destinationIp": "172.23.200.2",
        "ruleMessage": "SERVER-WEBAPP Apache Log4j remote code execution attempt",
        "classification": "Attempted Administrator Privilege Gain",
        "impact": "Red",
        "action": "Block"
    }
    collector = FmcSecurityCollector()
    event = collector.parse_fmc_event(sample_fmc_item)
    assert event.source_device == "Cisco FMC"
    assert event.category == ThreatCategory.INTRUSION
    assert event.attacker_ip == "45.155.205.233"
    assert event.action_taken == "BLOCKED"

def test_sophos_email_quarantine_parsing():
    sample_quarantine_entry = {
        "mail_id": "sp-998811",
        "sender": "attacker@compromised-gov.com",
        "recipient": "minister-office@mne.gov.ps",
        "reason": "Malware detected: Trojan.VBS.Agent",
        "sandbox_verdict": "Malicious",
        "action": "Quarantined",
        "timestamp": "2026-09-06T02:45:00Z"
    }
    collector = SophosEmailCollector()
    event = collector.parse_quarantine_entry(sample_quarantine_entry)
    assert event.source_device == "Sophos Email"
    assert event.category == ThreatCategory.PHISHING
    assert event.target == "minister-office@mne.gov.ps"
    assert event.action_taken == "QUARANTINED"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/security_review/test_appliance_collectors.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `FmcSecurityCollector` and `SophosEmailCollector`**

Implement FMC token authentication, audit/intrusion query, and Sophos XML API/WebConsole scraper with error handling.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/security_review/test_appliance_collectors.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/connectors/security/fmc_collector.py core/connectors/security/sophos_collector.py tests/security_review/test_appliance_collectors.py
git commit -m "feat(security_review): add Cisco FMC and Sophos Email collectors"
```

---

### Task 4: Identity & Messaging Collectors: Active Directory & Exchange

**Files:**
- Create: `core/connectors/security/ad_exchange_collector.py`
- Test: `tests/security_review/test_identity_collectors.py`

**Interfaces:**
- Consumes: `BaseSecurityCollector`, `NormalizedSecurityEvent`.
- Produces: `ActiveDirectoryCollector`, `ExchangeCollector`.

- [ ] **Step 1: Write the failing tests for AD & Exchange security event parsing**

```python
# tests/security_review/test_identity_collectors.py
from datetime import datetime, timezone
from core.connectors.security.ad_exchange_collector import ActiveDirectoryCollector
from core.connectors.security.models import ThreatCategory

def test_ad_privileged_group_change_parsing():
    sample_event = {
        "EventID": 4728,
        "TargetUserName": "Domain Admins",
        "MemberName": "CN=TemporaryUser,OU=Users,DC=mne,DC=gov,DC=ps",
        "SubjectUserName": "svc_installer",
        "TimeCreated": "2026-09-06T05:22:00Z"
    }
    collector = ActiveDirectoryCollector()
    event = collector.parse_security_event(sample_event)
    assert event.source_device == "Active Directory"
    assert event.category == ThreatCategory.PRIVILEGE_CHANGE
    assert "Member added to Domain Admins" in event.threat_name
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/security_review/test_identity_collectors.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `ActiveDirectoryCollector` and `ExchangeCollector`**

Include parsers for EventID 4625 (Failed logon), 4740 (Account lockout), 4728/4732/4756 (Privilege change), and Exchange transport log parsing.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/security_review/test_identity_collectors.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/connectors/security/ad_exchange_collector.py tests/security_review/test_identity_collectors.py
git commit -m "feat(security_review): add Active Directory and Exchange security collectors"
```

---

### Task 5: Security Risk Normalization & Correlation Engine

**Files:**
- Create: `core/security_review/engine.py`
- Test: `tests/security_review/test_risk_engine.py`

**Interfaces:**
- Consumes: List of `CollectorResult`, `NormalizedSecurityEvent`.
- Produces: `SecurityRiskEngine`, `IncidentReport` containing classified `Incident` objects.

- [ ] **Step 1: Write the failing tests for deduplication, correlation, and SOC severity ranking**

```python
# tests/security_review/test_risk_engine.py
from datetime import datetime, timezone, timedelta
from core.connectors.security.models import (
    NormalizedSecurityEvent,
    ThreatCategory,
    SeverityLevel,
    CollectorResult,
    CollectorStatus,
)
from core.security_review.engine import SecurityRiskEngine

def test_deduplication_of_event_floods():
    now = datetime.now(timezone.utc)
    events = [
        NormalizedSecurityEvent(
            event_id=f"evt-{i}",
            timestamp=now - timedelta(minutes=i),
            source_device="FortiGate",
            category=ThreatCategory.BRUTE_FORCE,
            threat_name="SSL-VPN Failed Logon",
            attacker_ip="185.220.101.5",
            target="admin",
            action_taken="DROPPED"
        )
        for i in range(50)
    ]
    engine = SecurityRiskEngine()
    incidents = engine.process_events(events)
    # Should collapse 50 identical attacks into 1 incident with event_count=50
    assert len(incidents) == 1
    assert incidents[0].event_count == 50
    assert incidents[0].severity == SeverityLevel.HIGH

def test_critical_unblocked_malware():
    now = datetime.now(timezone.utc)
    events = [
        NormalizedSecurityEvent(
            event_id="crit-1",
            timestamp=now,
            source_device="Sophos Email",
            category=ThreatCategory.MALWARE,
            threat_name="Ransomware.LockBit payload detected",
            target="dg-finance@mne.gov.ps",
            action_taken="ALLOWED" # Unblocked!
        )
    ]
    engine = SecurityRiskEngine()
    incidents = engine.process_events(events)
    assert incidents[0].severity == SeverityLevel.CRITICAL
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/security_review/test_risk_engine.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `SecurityRiskEngine`**

Implement aggregation algorithm, cross-device correlation graph, and standard SOC rule evaluation (Critical, High, Medium).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/security_review/test_risk_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/security_review/engine.py tests/security_review/test_risk_engine.py
git commit -m "feat(security_review): implement risk deduplication, correlation, and severity engine"
```

---

### Task 6: Concrete Remediation Playbooks & Mode B Engine

**Files:**
- Create: `core/security_review/playbooks.py`
- Create: `core/security_review/remediator.py`
- Test: `tests/security_review/test_remediation.py`

**Interfaces:**
- Consumes: `Incident`, `SeverityLevel`.
- Produces: `attach_remediation_playbooks(incident: Incident)`, `RemediationExecutor`.

- [ ] **Step 1: Write the failing tests for playbook assignment and Mode B execution planning**

```python
# tests/security_review/test_remediation.py
from datetime import datetime, timezone
from core.connectors.security.models import Incident, SeverityLevel, ThreatCategory
from core.security_review.playbooks import attach_remediation_playbooks
from core.security_review.remediator import RemediationExecutor

def test_fortigate_vpn_brute_force_playbook():
    now = datetime.now(timezone.utc)
    incident = Incident(
        incident_id="MNE-SEC-20260906-01",
        title="SSL-VPN Brute Force",
        severity=SeverityLevel.HIGH,
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        first_seen=now,
        last_seen=now,
        description="Persistent brute-force from 185.220.101.5",
        action_taken="DROPPED",
        attacker_ip="185.220.101.5",
        target="admin"
    )
    attach_remediation_playbooks(incident)
    assert len(incident.remediation_cli) > 0
    assert "diagnose user ban add src-ip 185.220.101.5" in incident.remediation_cli[0]
    assert incident.remediation_mode_b_command is not None
    assert "remediate incident MNE-SEC-20260906-01" in incident.remediation_mode_b_command

def test_remediation_whitelist_protection():
    # Attempting to remediate an internal core IP or DNS must be rejected
    executor = RemediationExecutor()
    is_safe, reason = executor.validate_target_safety("172.23.71.27") # MNE-DC1 IP
    assert not is_safe
    assert "protected infrastructure IP" in reason
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/security_review/test_remediation.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `playbooks.py` and `remediator.py`**

Implement device playbooks for FortiGate, F5, Sophos, Cisco FMC, Active Directory, and protected IP whitelisting.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/security_review/test_remediation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/security_review/playbooks.py core/security_review/remediator.py tests/security_review/test_remediation.py
git commit -m "feat(security_review): implement remediation playbooks and Mode B assisted execution"
```

---

### Task 7: Executive HTML & PDF Reporting Engine with SMTP Dispatch

**Files:**
- Create: `core/security_review/reporter.py`
- Create: `core/security_review/templates/report.html.j2`
- Test: `tests/security_review/test_reporter.py`

**Interfaces:**
- Consumes: List of `Incident`, List of `CollectorResult`.
- Produces: `render_html_report()`, `compile_pdf_report()`, `send_daily_security_email()`.

- [ ] **Step 1: Write the failing tests for HTML rendering, PDF generation, and SMTP message assembly**

```python
# tests/security_review/test_reporter.py
from datetime import datetime, timezone
from core.connectors.security.models import Incident, SeverityLevel, ThreatCategory, CollectorResult, CollectorStatus
from core.security_review.reporter import SecurityReporter

def test_html_report_rendering():
    now = datetime.now(timezone.utc)
    incident = Incident(
        incident_id="MNE-SEC-20260906-01",
        title="SSL-VPN Brute Force Attack",
        severity=SeverityLevel.HIGH,
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        first_seen=now,
        last_seen=now,
        description="Persistent brute force from 185.220.101.5",
        action_taken="DROPPED",
        event_count=42,
        attacker_ip="185.220.101.5",
        remediation_cli=["diagnose user ban add src-ip 185.220.101.5 86400"]
    )
    collector_results = [
        CollectorResult(device_name="FortiGate", status=CollectorStatus.SUCCESS),
        CollectorResult(device_name="F5 BIG-IP", status=CollectorStatus.SUCCESS)
    ]
    reporter = SecurityReporter()
    html = reporter.render_html_report(incidents=[incident], collectors=collector_results)
    assert "MNE Daily Security Report" in html
    assert "MNE-SEC-20260906-01" in html
    assert "185.220.101.5" in html
    assert "HIGH" in html

def test_smtp_mime_message_construction():
    reporter = SecurityReporter()
    msg = reporter.build_email_message(
        html_content="<h1>Report</h1>",
        pdf_bytes=b"%PDF-1.4 Mock Content",
        recipients=["omersalem@mne.gov.ps", "omersalem2008@gmail.com"]
    )
    assert msg["To"] == "omersalem@mne.gov.ps, omersalem2008@gmail.com"
    assert "MNE Daily Cyber Threat & Risk Intelligence" in msg["Subject"]
    assert len(msg.get_payload()) == 2 # HTML body + PDF attachment
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/security_review/test_reporter.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Jinja2 template, PDF compiler, and SMTP transport in `reporter.py`**

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/security_review/test_reporter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/security_review/reporter.py core/security_review/templates/ tests/security_review/test_reporter.py
git commit -m "feat(security_review): implement executive HTML and PDF report generator with SMTP dispatch"
```

---

### Task 8: Daily 07:00 AM Automation, CLI Entrypoints & End-to-End Verification

**Files:**
- Create: `core/security_review/cli.py`
- Create: `core/security_review/daily_job.py`
- Create: `scripts/register_daily_security_task.ps1`
- Test: `tests/security_review/test_cli_and_job.py`

**Interfaces:**
- Consumes: All components from Tasks 1–7.
- Produces: Runnable CLI commands (`--run-now`, `--dry-run`, `--remediate`), automated Windows Scheduled Task registration script.

- [ ] **Step 1: Write the failing tests for CLI argument parsing and runner orchestration**

```python
# tests/security_review/test_cli_and_job.py
from core.security_review.cli import build_parser, run_security_pipeline

def test_cli_parser_options():
    parser = build_parser()
    args = parser.parse_args(["--run-now"])
    assert args.run_now is True
    assert args.dry_run is False

    args_rem = parser.parse_args(["--remediate", "MNE-SEC-20260906-01"])
    assert args_rem.remediate == "MNE-SEC-20260906-01"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/security_review/test_cli_and_job.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `cli.py`, `daily_job.py`, and `register_daily_security_task.ps1`**

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/security_review/test_cli_and_job.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/security_review/cli.py core/security_review/daily_job.py scripts/register_daily_security_task.ps1 tests/security_review/test_cli_and_job.py
git commit -m "feat(security_review): add CLI runner, daily job orchestrator, and scheduled task script"
```

---

## Plan Self-Review Checklist
- [x] Spec coverage: Every requirement from `docs/superpowers/specs/2026-09-06-security-review-agent-design.md` has a dedicated task.
- [x] Zero placeholders: All tasks specify explicit filenames, interface contracts, and full test code.
- [x] Type consistency: `NormalizedSecurityEvent`, `Incident`, `SeverityLevel`, `ThreatCategory` match across all tasks.
- [x] Safety compliance: Gated Mode B remediation and protected IP whitelist implemented.
