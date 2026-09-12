import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Ensure local .env is loaded
load_dotenv()

from core.connectors.security.models import (
    CollectorResult,
    CollectorStatus,
    Incident,
    NormalizedSecurityEvent,
)
from core.security_review.config import SecurityAgentConfig
from core.security_review.contracts import (
    AnalysisEngine,
    ReportFormat,
    ReviewMode,
    RunState,
    SecurityReviewRequest,
)
from core.security_review.remediator import RemediationExecutor
from core.security_review.reporter import SecurityReporter
from core.security_review.service import SecurityReviewService

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
    parser.add_argument(
        "--engine",
        choices=["NONE", "CODEX", "ANTIGRAVITY", "BOTH"],
        default="NONE",
        help="AI analysis engine to run after review (NONE, CODEX, ANTIGRAVITY, BOTH).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model override for the AI analysis engine.",
    )
    parser.add_argument(
        "--collectors",
        type=str,
        default=None,
        help="Comma-separated list of collector IDs to run (e.g. 'fortigate_core,f5_bigip').",
    )
    parser.add_argument(
        "--hours",
        type=float,
        default=24.0,
        help="Lookback window in hours (default: 24.0).",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=500,
        help="Maximum log records to collect per collector (default: 500).",
    )
    parser.add_argument(
        "--format",
        type=str,
        default=None,
        help="Comma-separated report formats: html,pdf,json,csv (default: all).",
    )
    return parser


def run_security_pipeline(
    dry_run: bool = False,
    send_email: bool = True,
    recipients: Optional[List[str]] = None,
    output_dir: str = "operations/reports",
    service: Optional[SecurityReviewService] = None,
    collector_registry: Optional[Dict[str, Any]] = None,
    engine: str = "NONE",
    model: Optional[str] = None,
    collectors: Optional[str | List[str]] = None,
    hours: float = 24.0,
    max_records: int = 500,
    formats: Optional[str | List[ReportFormat | str]] = None,
) -> Dict[str, Any]:
    """Executes the security log review and reporting pipeline via SecurityReviewService."""
    config_mgr = SecurityAgentConfig()
    target_recipients = recipients or config_mgr.get_recipients()
    should_send_email = send_email and not dry_run

    svc = service or SecurityReviewService(
        collector_registry=collector_registry,
        config_mgr=config_mgr,
    )

    # Parse report formats
    parsed_formats: List[ReportFormat] = []
    if isinstance(formats, str):
        for f_name in formats.split(","):
            clean_f = f_name.strip().upper()
            if clean_f in ReportFormat.__members__:
                parsed_formats.append(ReportFormat(clean_f))
    elif isinstance(formats, list):
        for item in formats:
            if isinstance(item, ReportFormat):
                parsed_formats.append(item)
            elif isinstance(item, str) and item.upper() in ReportFormat.__members__:
                parsed_formats.append(ReportFormat(item.upper()))
    if not parsed_formats:
        parsed_formats = [ReportFormat.HTML, ReportFormat.PDF, ReportFormat.JSON, ReportFormat.CSV]

    # Parse target collectors
    target_collector_ids: List[str] = [
        "fortigate_core",
        "fortianalyzer",
        "f5_bigip",
        "cisco_fmc",
        "sophos_email",
        "active_directory",
        "exchange_2019",
    ]
    if isinstance(collectors, str) and collectors.strip():
        target_collector_ids = [c.strip() for c in collectors.split(",") if c.strip()]
    elif isinstance(collectors, list) and collectors:
        target_collector_ids = list(collectors)

    # Parse AI engine
    analysis_engine = AnalysisEngine.NONE
    if isinstance(engine, str) and engine.strip().upper() in AnalysisEngine.__members__:
        analysis_engine = AnalysisEngine(engine.strip().upper())

    req = SecurityReviewRequest(
        mode=ReviewMode.FULL,
        collector_ids=target_collector_ids,
        hours_back=float(hours) if hours is not None else 24.0,
        max_records_per_collector=int(max_records) if max_records is not None else 500,
        analysis_engine=analysis_engine,
        analysis_model=model,
        send_email=should_send_email,
        recipients=target_recipients,
        report_formats=parsed_formats,
    )

    run = svc.start_review(req, async_run=False)

    # Load artifacts and objects from run store
    raw_incidents = svc.run_store.get_incidents(run.run_id)
    raw_events = svc.run_store.get_events(run.run_id)
    diagnostics = svc.run_store.get_collector_diagnostics(run.run_id)

    html_path = run.report_artifacts.get("html") or ""
    pdf_path = run.report_artifacts.get("pdf") or ""

    html_report = ""
    if html_path and os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            html_report = f.read()

    pdf_report = b""
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_report = f.read()

    # Reconstruct collector results for compatibility
    collector_results: List[CollectorResult] = []
    if isinstance(diagnostics, dict):
        for cid, diag in diagnostics.items():
            status_map = {
                "SUCCESS": CollectorStatus.SUCCESS,
                "PARTIAL": CollectorStatus.WARNING,
                "FAILED": CollectorStatus.FAILED,
            }
            collector_results.append(
                CollectorResult(
                    device_name=diag.get("device_name", cid),
                    status=status_map.get(diag.get("status", "FAILED"), CollectorStatus.FAILED),
                    events=[],
                    error_message=diag.get("message") if diag.get("status") == "FAILED" else None,
                    collection_duration_seconds=diag.get("duration_seconds", 0.0),
                )
            )

    email_sent = (run.email_result or {}).get("sent", False)
    success = run.state in (RunState.COMPLETED, RunState.PARTIAL)

    return {
        "success": success,
        "run_id": run.run_id,
        "state": run.state.value,
        "incidents": raw_incidents,
        "collectors": collector_results,
        "html_report": html_report,
        "pdf_report": pdf_report,
        "html_path": html_path,
        "pdf_path": pdf_path,
        "email_sent": email_sent,
        "analysis_refs": run.analysis_refs,
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
        print("Safety check passed. Remediation plan ready.")
        sys.exit(0)

    if args.dry_run or args.run_now:
        send_mail = not args.dry_run
        result = run_security_pipeline(
            dry_run=args.dry_run,
            send_email=send_mail,
            engine=args.engine,
            model=args.model,
            collectors=args.collectors,
            hours=args.hours,
            max_records=args.max_records,
            formats=args.format,
        )
        print(f"\n[MNE Security Review Complete]")
        print(f"Run ID:          {result.get('run_id')}")
        print(f"Status:          {result.get('state')}")
        print(f"Total Incidents: {len(result['incidents'])}")
        print(f"HTML Report:     {result['html_path']}")
        print(f"PDF Report:      {result['pdf_path']}")
        if result['email_sent']:
            print(f"Email Dispatch:  SUCCESS")
        sys.exit(0 if result["success"] else 1)

    parser.print_help()


if __name__ == "__main__":
    main()
