from datetime import datetime, timezone
from core.connectors.security.models import (
    Incident,
    SeverityLevel,
    ThreatCategory,
    CollectorResult,
    CollectorStatus,
)
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
        target="admin",
        remediation_cli=["diagnose user ban add src-ip 185.220.101.5 86400"],
        remediation_gui=["1. Navigate to FortiGate GUI", "2. Add to G_BLACK_LIST"],
        remediation_mode_b_command="remediate incident MNE-SEC-20260906-01"
    )
    collector_results = [
        CollectorResult(device_name="FortiGate", status=CollectorStatus.SUCCESS),
        CollectorResult(device_name="F5 BIG-IP", status=CollectorStatus.SUCCESS),
        CollectorResult(device_name="Cisco FMC", status=CollectorStatus.SUCCESS),
        CollectorResult(device_name="Sophos Email", status=CollectorStatus.SUCCESS),
        CollectorResult(device_name="Active Directory", status=CollectorStatus.SUCCESS),
        CollectorResult(device_name="Exchange", status=CollectorStatus.SUCCESS),
    ]
    reporter = SecurityReporter()
    html = reporter.render_html_report(incidents=[incident], collectors=collector_results)
    assert "Ministry of National Economy" in html
    assert "MNE-SEC-20260906-01" in html
    assert "185.220.101.5" in html
    assert "HIGH" in html
    assert "diagnose user ban add" in html

def test_smtp_mime_message_construction():
    reporter = SecurityReporter()
    msg = reporter.build_email_message(
        html_content="<h1>MNE Security Report</h1>",
        pdf_bytes=b"%PDF-1.4 Mock PDF Content",
        recipients=["omersalem@mne.gov.ps", "omersalem2008@gmail.com"],
        subject_date_str="2026-09-06"
    )
    assert msg["To"] == "omersalem@mne.gov.ps, omersalem2008@gmail.com"
    assert "MNE Daily Cyber Threat & Risk Intelligence" in msg["Subject"]
    # Check that it is multipart with HTML and PDF
    payloads = msg.get_payload()
    assert len(payloads) == 2
    # Verify PDF attachment headers
    pdf_part = payloads[1]
    assert "application/pdf" in pdf_part.get_content_type()
    assert "MNE_Daily_Security_Report_2026-09-06.pdf" in pdf_part.get_filename()

def test_pdf_compilation():
    reporter = SecurityReporter()
    pdf_bytes = reporter.compile_pdf_report("<html><body><h1>Test Report</h1></body></html>")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")


def test_analysis_html_report_rendering():
    reporter = SecurityReporter()
    sample_analysis = {
        "analysis_id": "an-test-12345",
        "engine": "ANTIGRAVITY",
        "model": "gemini-2.5-pro",
        "status": "COMPLETED",
        "confidence": 0.92,
        "run_id": "run-sec-20260912-001",
        "plain_summary": "Active brute force observed on perimeter SSL-VPN.",
        "affected_systems": ["FortiGate-Primary", "AD-DC01"],
        "affected_users": ["admin", "root"],
        "affected_branches": ["Headquarters"],
        "affected_services": ["SSL-VPN:4433"],
        "ranked_hypotheses": [
            {
                "hypothesis": "External credential stuffing attack against SSL-VPN",
                "likelihood": "HIGH",
                "explanation": "High volume of failed auth attempts from known bulletproof hosting.",
            }
        ],
        "observations": {
            "supporting": ["Repeated failed logins from 185.220.101.5", "Account lockout triggered"],
            "contradicting": ["No internal lateral movement detected"],
            "missing_evidence": ["NetFlow records for host during the spike"],
        },
        "recommended_diagnostics": ["diagnose user ban status", "get router info routing-table all"],
        "immediate_actions": ["Ban IP 185.220.101.5 on FortiGate for 24 hours"],
        "long_term_actions": ["Enforce MFA on SSL-VPN realm"],
        "sources_cited": ["FortiGate event log #40291", "Security review run-sec-20260912-001"],
    }
    html = reporter.generate_analysis_html_report(sample_analysis)
    assert "Ministry of National Economy" in html
    assert "an-test-12345" in html
    assert "ANTIGRAVITY" in html
    assert "gemini-2.5-pro" in html
    assert "92%" in html
    assert "External credential stuffing attack" in html
    assert "Ban IP 185.220.101.5" in html
    assert "@media print" in html


def test_analysis_pdf_compilation():
    reporter = SecurityReporter()
    sample_analysis = {
        "analysis_id": "an-test-12345",
        "engine": "ANTIGRAVITY",
        "model": "gemini-2.5-pro",
        "status": "COMPLETED",
        "confidence": 0.92,
        "run_id": "run-sec-20260912-001",
        "plain_summary": "Active brute force observed on perimeter SSL-VPN.",
        "affected_systems": ["FortiGate-Primary"],
        "affected_users": ["admin"],
        "affected_branches": ["HQ"],
        "affected_services": ["SSL-VPN"],
        "ranked_hypotheses": [
            {
                "hypothesis": "External credential stuffing attack",
                "likelihood": "HIGH",
                "explanation": "High volume of failed auth attempts.",
            }
        ],
        "observations": {
            "supporting": ["Repeated failed logins"],
            "contradicting": [],
            "missing_evidence": [],
        },
        "recommended_diagnostics": ["diagnose user ban status"],
        "immediate_actions": ["Ban IP"],
        "long_term_actions": ["Enforce MFA"],
        "sources_cited": ["FortiGate event log"],
    }
    pdf_bytes = reporter.compile_analysis_pdf_report(sample_analysis)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")

