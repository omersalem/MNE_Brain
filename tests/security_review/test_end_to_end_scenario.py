"""
Comprehensive End-to-End Fixture Scenario for MNE_Brain Security Subsystem.
Simulates a multi-vector threat environment:
- FortiGate VPN failure
- F5 WAF exploit attempt
- Cisco FMC intrusion event
- Active Directory account lockout
- Exchange collector failure (verifying PARTIAL state and targeted retry)
- Cross-run recurrence tracking (NEW -> RECURRING transition and stable fingerprints)
- Concurrent AI Multi-Engine Analysis comparison (Codex vs Antigravity)
- Reporting exports (Executive HTML, Technical HTML, PDF, JSON, CSV)
- P8 diagnostic troubleshooting handoff
- Zero live network sockets, zero credentials, zero SMTP traffic.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest

from core.connectors.security.models import (
    CollectorResult,
    CollectorStatus,
    NormalizedSecurityEvent,
    SeverityLevel,
    ThreatCategory,
)
from core.security_review.analysis_compare import compare_analyses
from core.security_review.analysis_pack import SecurityAnalysisPackBuilder
from core.security_review.contracts import (
    AnalysisEngine,
    ReportFormat,
    ReviewMode,
    RunState,
    SecurityReviewRequest,
)
from core.security_review.jobs import SecurityReviewJobManager
from core.security_review.reporter import SecurityReporter
from core.security_review.run_store import SecurityReviewRunStore
from core.security_review.service import SecurityReviewService
from core.security_review.trends import categorize_run_incidents_delta, get_trend_analytics
from core.security_review.troubleshooting_bridge import SecurityTroubleshootingBridge


class FakeScenarioCollector:
    """Configurable mock collector for deterministic end-to-end testing."""

    def __init__(self, device_name: str, events=None, fail: bool = False, error_msg: str = ""):
        self.device_name = device_name
        self.events = events or []
        self.fail = fail
        self.error_msg = error_msg

    def collect_logs(self, hours_back: int = 24) -> CollectorResult:
        if self.fail:
            return CollectorResult(
                device_name=self.device_name,
                status=CollectorStatus.FAILED,
                error_message=self.error_msg or f"Simulated failure on {self.device_name}",
                events=[],
                collection_duration_seconds=0.05,
            )
        return CollectorResult(
            device_name=self.device_name,
            status=CollectorStatus.SUCCESS,
            events=self.events,
            collection_duration_seconds=0.02,
        )


def test_full_security_review_end_to_end_scenario(tmp_path):
    repo_root = Path(__file__).resolve().parent.parent.parent
    run_store = SecurityReviewRunStore(tmp_path / "runs")
    incident_store = run_store.incident_store
    job_manager = SecurityReviewJobManager()
    now = datetime.now(timezone.utc)

    # 1. Build Multi-Vector Threat Events
    vpn_event = NormalizedSecurityEvent(
        event_id="fg-vpn-01",
        timestamp=now - timedelta(minutes=45),
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        threat_name="SSL-VPN Failed Authentication Storm",
        attacker_ip="185.220.101.5",
        target="admin",
        action_taken="BLOCKED",
        raw_snippet="SSL-VPN login failed for user admin from 185.220.101.5",
        metadata={"reason": "credential_stuffing", "proto": "ssl-vpn"},
    )

    f5_event = NormalizedSecurityEvent(
        event_id="f5-waf-01",
        timestamp=now - timedelta(minutes=30),
        source_device="F5 BIG-IP",
        category=ThreatCategory.WAF_EXPLOIT,
        threat_name="SQL Injection Pattern in URI Parameter",
        attacker_ip="198.51.100.77",
        target="web-portal.mne.gov.ps",
        action_taken="BLOCKED",
        raw_snippet="ASM: SQL Injection attempt detected in URI parameter id",
        metadata={"uri": "/portal/login.php?id=1' UNION SELECT", "rule": "asm_sqli_01"},
    )

    fmc_event = NormalizedSecurityEvent(
        event_id="fmc-ips-01",
        timestamp=now - timedelta(minutes=20),
        source_device="Cisco FMC",
        category=ThreatCategory.INTRUSION,
        threat_name="TCP SYN Flood / Port Scan Anomaly",
        attacker_ip="198.51.100.44",
        target="fw-fortigate-edge-01",
        action_taken="DROPPED",
        raw_snippet="SNORT: TCP SYN flood detected targeting edge interface",
        metadata={"ports": "22,80,443,8443,3389"},
    )

    ad_event = NormalizedSecurityEvent(
        event_id="ad-sec-01",
        timestamp=now - timedelta(minutes=10),
        source_device="Active Directory",
        category=ThreatCategory.BRUTE_FORCE,
        threat_name="Domain Account Lockout Exceeded",
        attacker_ip="10.0.0.50",
        target="dc-windows-ad-01",
        action_taken="BLOCKED",
        raw_snippet="Event 4740: A user account was locked out finance_svc",
        metadata={"event_id": 4740, "account": "finance_svc"},
    )

    # 2. Setup Collectors Registry with one failing collector
    exchange_collector = FakeScenarioCollector("Exchange", fail=True, error_msg="Connection timed out to 172.23.71.36:25")
    registry = {
        "fortigate_core": FakeScenarioCollector("FortiGate", [vpn_event]),
        "f5_bigip": FakeScenarioCollector("F5 BIG-IP", [f5_event]),
        "cisco_fmc": FakeScenarioCollector("Cisco FMC", [fmc_event]),
        "active_directory": FakeScenarioCollector("Active Directory", [ad_event]),
        "exchange_2019": exchange_collector,
    }

    service = SecurityReviewService(
        run_store=run_store,
        job_manager=job_manager,
        collector_registry=registry,
    )

    # 3. Execution of Run 1 (Partial due to Exchange failure)
    req1 = SecurityReviewRequest(
        mode=ReviewMode.FULL,
        collector_ids=["fortigate_core", "f5_bigip", "cisco_fmc", "active_directory", "exchange_2019"],
        hours_back=24.0,
        analysis_engine=AnalysisEngine.NONE,
        send_email=False,
        report_formats=[ReportFormat.HTML, ReportFormat.JSON, ReportFormat.CSV],
    )

    run1 = service.start_review(req1, async_run=False)

    assert run1.state == RunState.PARTIAL
    assert run1.stage == "COMPLETED_PARTIAL"
    assert len(run1.collector_diagnostics) == 5
    assert run1.collector_diagnostics["exchange_2019"]["status"] == "FAILED"
    assert run1.collector_diagnostics["fortigate_core"]["status"] == "SUCCESS"

    # Verify incidents generated in Run 1
    run1_incidents = run_store.get_incidents(run1.run_id)
    assert len(run1_incidents) >= 3

    # 4. Targeted Retry for Failed Collector (Exchange)
    exchange_collector.fail = False
    exchange_collector.events = [
        NormalizedSecurityEvent(
            event_id="ex-01",
            timestamp=now - timedelta(minutes=5),
            source_device="Exchange",
            category=ThreatCategory.SYSTEM_HEALTH,
            threat_name="Mailbox Store Online",
            attacker_ip="",
            target="exchange-01",
            action_taken="ALLOWED",
        )
    ]

    retry_run = service.retry_review(run1.run_id, only_failed=True, async_run=False)
    assert retry_run.state == RunState.COMPLETED
    assert retry_run.collector_diagnostics["exchange_2019"]["status"] == "SUCCESS"

    # 5. Run 2 (Verify Recurrence & Stable Fingerprinting)
    # The VPN attack repeats in Run 2
    vpn_repeat_event = NormalizedSecurityEvent(
        event_id="fg-vpn-02",
        timestamp=now,
        source_device="FortiGate",
        category=ThreatCategory.BRUTE_FORCE,
        threat_name="SSL-VPN Failed Authentication Storm",
        attacker_ip="185.220.101.5",
        target="admin",
        action_taken="BLOCKED",
    )
    registry["fortigate_core"].events = [vpn_repeat_event]

    req2 = SecurityReviewRequest(
        mode=ReviewMode.FULL,
        collector_ids=["fortigate_core"],
        hours_back=1.0,
        analysis_engine=AnalysisEngine.NONE,
        send_email=False,
        report_formats=[ReportFormat.HTML],
    )
    run2 = service.start_review(req2, async_run=False)
    assert run2.state == RunState.COMPLETED

    run2_incidents = run_store.get_incidents(run2.run_id)
    vpn_inc = next((i for i in run2_incidents if i.get("category") == "BRUTE_FORCE" and "VPN" in i.get("title", "")), None)
    assert vpn_inc is not None

    vpn_fp = vpn_inc.get("fingerprint")
    assert vpn_fp is not None

    # Verify IncidentStore tracked the recurrence
    saved_rec = incident_store.get_incident(vpn_fp)
    assert saved_rec is not None
    assert saved_rec.occurrence_count == 2
    assert saved_rec.lifecycle_state == "RECURRING"

    # 6. Delta Tracking between Runs
    delta = categorize_run_incidents_delta(run2.run_id, run_store)
    assert delta["run_id"] == run2.run_id
    assert delta["prior_run_id"] == retry_run.run_id or delta["prior_run_id"] == run1.run_id
    assert len(delta["recurring_incidents"]) >= 1

    # 7. AI Multi-Engine Analysis & Comparison Card Simulation
    pack_builder = SecurityAnalysisPackBuilder(run_store=run_store, base_dir=repo_root)
    analysis_pack = pack_builder.build_incident_pack(vpn_fp)
    assert vpn_fp in analysis_pack["incident_fingerprints"]

    mock_codex_output = {
        "engine": "CODEX",
        "provider": "openai",
        "model": "gpt-4o",
        "status": "COMPLETED",
        "confidence": 0.92,
        "hypotheses": [
            {"hypothesis": "External password spraying attack targeting admin account", "confidence": 0.92},
            {"hypothesis": "Compromised credential list validation attempt", "confidence": 0.85},
        ],
        "common_conclusions": ["Sustained brute force attack from 185.220.101.5"],
        "recommended_diagnostics": ["diagnose user ban status", "diagnose vpn ssl list"],
        "unresolved_questions": ["Is 185.220.101.5 a Tor exit node or commercial VPN?"],
    }

    mock_antigravity_output = {
        "engine": "ANTIGRAVITY",
        "provider": "google",
        "model": "gemini-2.5-flash",
        "status": "COMPLETED",
        "confidence": 0.95,
        "hypotheses": [
            {"hypothesis": "External automated credential stuffing attack on SSL-VPN", "confidence": 0.95},
            {"hypothesis": "Botnet distributed scan hitting perimeter gateway", "confidence": 0.80},
        ],
        "common_conclusions": ["Sustained brute force attack from 185.220.101.5"],
        "recommended_diagnostics": ["diagnose user ban status", "show firewall policy 42"],
        "unresolved_questions": ["Verify whether MFA was triggered for the account."],
    }

    comparison = compare_analyses(mock_codex_output, mock_antigravity_output)
    assert "comparison_id" in comparison
    assert len(comparison["common_conclusions"]) >= 1
    assert "diagnose user ban status" in comparison["shared_diagnostics"]
    assert len(comparison["unresolved_questions"]) >= 1

    # 8. Report Generation & Exports Validation
    reporter = SecurityReporter()

    exec_html = reporter.generate_executive_report(run2.run_id, run_store)
    assert "Executive Cyber Threat & Risk Briefing" in exec_html
    assert "Ministry of National Economy" in exec_html

    tech_html = reporter.generate_technical_report(run2.run_id, run_store)
    assert "MNE Technical Security Operations Report" in tech_html
    assert "Perimeter & Identity Log Diagnostics" in tech_html

    json_export = reporter.generate_json_export(run2.run_id, run_store)
    assert json_export["run_id"] == run2.run_id
    assert len(json_export["incidents"]) >= 1

    csv_export = reporter.generate_csv_incident_export(run2.run_id, run_store)
    assert "fingerprint,display_id,title" in csv_export
    assert "185.220.101.5" in csv_export

    pdf_bytes = reporter.compile_pdf_report(
        incidents=run2_incidents,
        collectors=run2.collector_diagnostics,
    )
    assert pdf_bytes.startswith(b"%PDF-")

    # 9. P8 Diagnostic Troubleshooting Bridge Handoff
    bridge = SecurityTroubleshootingBridge(
        base_dir=repo_root,
        run_store=run_store,
        incident_store=incident_store,
    )

    handoff = bridge.start_troubleshooting(fingerprint=vpn_fp, execute_p9=False)
    assert handoff["target_canonical"] in ("fw-fortigate-edge-01", "fw-fortigate-hq-01")
    assert handoff["scenario"] == "p8-vpn-access"
    assert handoff["binding"] == "p7-fortigate-edge"
    assert len(handoff["p8_plan"]["planned_checks"]) > 0
    assert "suggested_ai_prompt" in handoff["ai_handoff"]

    # Verify timeline records the handoff
    timeline = incident_store.get_timeline(vpn_fp)
    timeline_types = [t.get("type") for t in timeline]
    assert "TROUBLESHOOTING_HANDOFF" in timeline_types
