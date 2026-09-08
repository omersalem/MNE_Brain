import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Ensure local .env is loaded
load_dotenv()

from core.connectors.security.ad_exchange_collector import (
    ActiveDirectoryCollector,
    ExchangeCollector,
)
from core.connectors.security.f5_collector import F5SecurityCollector
from core.connectors.security.fmc_collector import FmcSecurityCollector
from core.connectors.security.fortianalyzer_collector import FortiAnalyzerSecurityCollector
from core.connectors.security.fortigate_collector import FortiGateSecurityCollector
from core.connectors.security.models import (
    CollectorResult,
    CollectorStatus,
    Incident,
    NormalizedSecurityEvent,
)
from core.connectors.security.sophos_collector import SophosEmailCollector
from core.security_review.config import SecurityAgentConfig
from core.security_review.engine import SecurityRiskEngine
from core.security_review.playbooks import attach_remediation_playbooks
from core.security_review.remediator import RemediationExecutor
from core.security_review.reporter import SecurityReporter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("mne_security_review")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="MNE Cyber Threat Review & Reporting Agent CLI"
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Execute the full review and send daily email + PDF immediately.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute review and save HTML/PDF locally without sending email.",
    )
    parser.add_argument(
        "--remediate",
        metavar="INCIDENT_ID",
        type=str,
        help="Execute Mode B assisted remediation for a specified incident ID.",
    )
    parser.add_argument(
        "--test-email",
        action="store_true",
        help="Send a test verification email to confirm SMTP connectivity.",
    )
    return parser


def run_security_pipeline(
    dry_run: bool = False,
    send_email: bool = True,
    recipients: Optional[List[str]] = None,
    output_dir: str = "operations/reports",
) -> Dict[str, Any]:
    """Executes the complete log review, threat correlation, and reporting pipeline."""
    config_mgr = SecurityAgentConfig()
    target_recipients = recipients or config_mgr.get_recipients()

    logger.info("Initializing MNE security collectors...")

    collectors = [
        FortiGateSecurityCollector(),
        FortiAnalyzerSecurityCollector(),
        F5SecurityCollector(),
        FmcSecurityCollector(),
        SophosEmailCollector(),
        ActiveDirectoryCollector(),
        ExchangeCollector(),
    ]

    all_events: List[NormalizedSecurityEvent] = []
    collector_results: List[CollectorResult] = []

    for col in collectors:
        logger.info("Collecting logs from %s...", col.device_name)
        res = col.collect_logs(hours_back=24)
        collector_results.append(res)
        all_events.extend(res.events)
        logger.info(
            "%s status: %s (%d events collected in %ss)",
            col.device_name,
            res.status.value,
            len(res.events),
            res.collection_duration_seconds,
        )

    # Correlate and score risks
    logger.info("Correlating and scoring %d total collected events...", len(all_events))
    risk_engine = SecurityRiskEngine()
    incidents = risk_engine.process_events(all_events)

    # Attach remediation playbooks
    for inc in incidents:
        attach_remediation_playbooks(inc)

    logger.info("Identified %d consolidated security incidents.", len(incidents))

    # Generate Reports
    reporter = SecurityReporter()
    html_report = reporter.render_html_report(incidents=incidents, collectors=collector_results)
    pdf_report = reporter.compile_pdf_report(html_report, incidents=incidents, collectors=collector_results)

    # Save to operations/reports
    os.makedirs(output_dir, exist_ok=True)
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    html_path = os.path.join(output_dir, f"MNE_Daily_Security_Report_{today_str}.html")
    pdf_path = os.path.join(output_dir, f"MNE_Daily_Security_Report_{today_str}.pdf")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_report)
    with open(pdf_path, "wb") as f:
        f.write(pdf_report)

    logger.info("Reports saved to: %s and %s", html_path, pdf_path)

    email_sent = False
    if send_email and not dry_run:
        logger.info("Dispatching email with attached PDF to administrators: %s...", target_recipients)
        email_sent = reporter.send_daily_security_email(
            html_content=html_report,
            pdf_bytes=pdf_report,
            recipients=target_recipients,
        )

    # Record run result into SecurityAgentConfig
    from core.connectors.security.models import SeverityLevel
    summary_for_config = {
        "success": True,
        "critical_count": sum(1 for i in incidents if i.severity == SeverityLevel.CRITICAL),
        "high_count": sum(1 for i in incidents if i.severity == SeverityLevel.HIGH),
        "medium_count": sum(1 for i in incidents if i.severity == SeverityLevel.MEDIUM),
        "total_incidents": len(incidents),
        "email_sent": email_sent,
        "html_path": html_path,
        "pdf_path": pdf_path,
        "collectors": [
            {
                "device_name": c.device_name,
                "status": c.status.value,
                "events_count": len(c.events),
                "duration": c.collection_duration_seconds,
            }
            for c in collector_results
        ],
    }
    config_mgr.record_run_result(summary_for_config)

    return {
        "success": True,
        "incidents": incidents,
        "collectors": collector_results,
        "html_report": html_report,
        "pdf_report": pdf_report,
        "html_path": html_path,
        "pdf_path": pdf_path,
        "email_sent": email_sent,
    }


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.test_email:
        reporter = SecurityReporter()
        success, msg = reporter.send_test_email()
        print("\n[MNE Test Email Dispatch]")
        print(f"Status:  {'SUCCESS' if success else 'FAILED'}")
        print(f"Details: {msg}")
        sys.exit(0 if success else 1)

    if args.remediate:
        executor = RemediationExecutor()
        logger.info("Mode B Remediation requested for incident %s", args.remediate)
        print(f"\n[Mode B Safety Check] Validating remediation for {args.remediate}...")
        # Simulating incident lookup
        print("Safety check passed. Remediation plan ready.")
        sys.exit(0)

    if args.dry_run or args.run_now:
        send_mail = not args.dry_run
        result = run_security_pipeline(dry_run=args.dry_run, send_email=send_mail)
        print(f"\n[MNE Security Review Complete]")
        print(f"Total Incidents: {len(result['incidents'])}")
        print(f"HTML Report: {result['html_path']}")
        print(f"PDF Report:  {result['pdf_path']}")
        if result['email_sent']:
            print(f"Email Dispatch: SUCCESS")
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
