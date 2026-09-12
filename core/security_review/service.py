"""
Security Review Service for MNE_Brain Release 2.
Single orchestration entry point for Security Agent runs (GUI, CLI, and Scheduler).
Accepts dependency injection for testability and manages the complete pipeline:
validation, background jobs, collection, correlation, persistence, analysis, reporting, and email.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.connectors.security.models import (
    CollectorRequest,
    CollectorResult,
    CollectorStatus,
    Incident,
    NormalizedSecurityEvent,
    SeverityLevel,
)
from core.security_review.ai_analyzer import SecurityAIAnalyzer
from core.security_review.config import SecurityAgentConfig
from core.security_review.contracts import (
    CollectorDiagnostic,
    DiagnosticStage,
    DiagnosticStatus,
    ReportFormat,
    ReviewMode,
    RunState,
    SecurityReviewRequest,
    SecurityReviewRun,
)
from core.security_review.engine import SecurityRiskEngine
from core.security_review.jobs import SecurityReviewJobManager
from core.security_review.playbooks import attach_remediation_playbooks
from core.security_review.reporter import SecurityReporter
from core.security_review.run_store import SecurityReviewRunStore
from core.security_review.identity_enrichment import LocalAttackerIdentityResolver

logger = logging.getLogger(__name__)

CANONICAL_COLLECTOR_MAP = {
    "fortigate_core": "FortiGate",
    "fortianalyzer": "FortiAnalyzer",
    "f5_bigip": "F5 BIG-IP",
    "cisco_fmc": "Cisco FMC",
    "sophos_email": "Sophos Email",
    "active_directory": "Active Directory",
    "exchange_2019": "Exchange",
}


def _default_collector_factory(collector_id: str) -> Any:
    """Instantiates live connectors on demand."""
    if collector_id == "fortigate_core":
        from core.connectors.security.fortigate_collector import FortiGateSecurityCollector
        return FortiGateSecurityCollector()
    elif collector_id == "fortianalyzer":
        from core.connectors.security.fortianalyzer_collector import FortiAnalyzerSecurityCollector
        return FortiAnalyzerSecurityCollector()
    elif collector_id == "f5_bigip":
        from core.connectors.security.f5_collector import F5SecurityCollector
        return F5SecurityCollector()
    elif collector_id == "cisco_fmc":
        from core.connectors.security.fmc_collector import FmcSecurityCollector
        return FmcSecurityCollector()
    elif collector_id == "sophos_email":
        from core.connectors.security.sophos_collector import SophosEmailCollector
        return SophosEmailCollector()
    elif collector_id == "active_directory":
        from core.connectors.security.ad_exchange_collector import ActiveDirectoryCollector
        return ActiveDirectoryCollector()
    elif collector_id == "exchange_2019":
        from core.connectors.security.ad_exchange_collector import ExchangeCollector
        return ExchangeCollector()
    raise ValueError(f"Unknown collector ID: '{collector_id}'")


class SecurityReviewService:
    """Service orchestrator for running cybersecurity reviews, correlating incidents,
    producing reports, and dispatching alerts.
    """

    def __init__(
        self,
        run_store: Optional[SecurityReviewRunStore] = None,
        job_manager: Optional[SecurityReviewJobManager] = None,
        collector_registry: Optional[Dict[str, Any]] = None,
        reporter: Optional[SecurityReporter] = None,
        risk_engine: Optional[SecurityRiskEngine] = None,
        config_mgr: Optional[SecurityAgentConfig] = None,
        clock: Optional[Callable[[], datetime]] = None,
        ai_analyzer: Optional[SecurityAIAnalyzer] = None,
        identity_resolver: Optional[LocalAttackerIdentityResolver] = None,
        identity_bindings: Optional[Dict[str, Dict[str, Any]]] = None,
        identity_query_executor: Optional[Any] = None,
    ):
        self.run_store = run_store or SecurityReviewRunStore()
        self.job_manager = job_manager or SecurityReviewJobManager()
        self.collector_registry = collector_registry or {}
        self.reporter = reporter or SecurityReporter()
        self.risk_engine = risk_engine or SecurityRiskEngine()
        self.config_mgr = config_mgr or SecurityAgentConfig()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.ai_analyzer = ai_analyzer or SecurityAIAnalyzer(run_store=self.run_store, clock=self.clock)
        enrichment_cfg = self.config_mgr.get_identity_enrichment_config() if hasattr(self.config_mgr, "get_identity_enrichment_config") else {}
        default_adapters = None
        if identity_resolver is None:
            from core.security_review.identity_providers import create_identity_adapters
            default_adapters = create_identity_adapters(
                enrichment_cfg,
                bindings=identity_bindings,
                executor=identity_query_executor,
            )

        self.identity_resolver = identity_resolver or LocalAttackerIdentityResolver(
            adapters=default_adapters,
            local_cidrs=enrichment_cfg.get("local_cidrs"),
            excluded_cidrs=enrichment_cfg.get("excluded_cidrs"),
            source_priority=enrichment_cfg.get("source_priority"),
            enabled_sources=enrichment_cfg.get("enabled_sources"),
            per_source_timeout_seconds=enrichment_cfg.get("per_source_timeout_seconds", 5.0),
            overall_timeout_seconds=enrichment_cfg.get("overall_timeout_seconds", 15.0),
            event_time_tolerance_seconds=enrichment_cfg.get("event_time_tolerance_seconds", 3600),
            current_record_max_age_hours=enrichment_cfg.get("current_record_max_age_hours", 24),
            max_candidates=enrichment_cfg.get("max_candidates", 5),
            enable_cache=enrichment_cfg.get("in_run_caching", True),
        )


    def _get_collector_instance(self, collector_id: str) -> Any:
        if collector_id in self.collector_registry:
            cand = self.collector_registry[collector_id]
            if callable(cand) and not hasattr(cand, "collect_logs"):
                return cand()
            return cand
        return _default_collector_factory(collector_id)

    def generate_run_id(self) -> str:
        timestamp_str = self.clock().strftime("%Y%m%d-%H%M%S")
        uid = uuid.uuid4().hex[:6]
        return f"sec-run-{timestamp_str}-{uid}"

    _generate_run_id = generate_run_id

    def start_review(
        self,
        request: SecurityReviewRequest | Dict[str, Any],
        run_id: Optional[str] = None,
        async_run: bool = True,
        owner_session_digest: Optional[str] = None,
    ) -> SecurityReviewRun:
        """Enqueues and executes a security review run (asynchronously by default)."""
        req_obj = request if isinstance(request, SecurityReviewRequest) else SecurityReviewRequest.from_dict(request)
        req_obj.validate()

        actual_run_id = run_id or self._generate_run_id()
        created_at = self.clock().isoformat()

        run = SecurityReviewRun(
            run_id=actual_run_id,
            request=req_obj.to_dict(),
            state=RunState.QUEUED,
            stage="QUEUED",
            created_at=created_at,
            retry_of_run_id=req_obj.prior_run_id,
        )
        self.run_store.save_run(run)
        self.job_manager.emit_event(
            run_id=actual_run_id,
            event_type="run.queued",
            data={"run_id": actual_run_id, "state": RunState.QUEUED.value, "request": req_obj.to_dict()},
        )

        if async_run:
            self.job_manager.submit_job(actual_run_id, self._execute_pipeline, actual_run_id, req_obj, owner_session_digest)
        else:
            run = self._execute_pipeline(actual_run_id, req_obj, owner_session_digest)

        return run

    def run_review(
        self,
        request: SecurityReviewRequest | Dict[str, Any],
        run_id: Optional[str] = None,
        async_run: bool = False,
        owner_session_digest: Optional[str] = None,
    ) -> SecurityReviewRun:
        """Executes a security review run (synchronously by default)."""
        return self.start_review(request, run_id=run_id, async_run=async_run, owner_session_digest=owner_session_digest)

    def retry_review(
        self,
        prior_run_id: str,
        only_failed: bool = True,
        async_run: bool = True,
        owner_session_digest: Optional[str] = None,
    ) -> SecurityReviewRun:
        """Initiates a targeted retry run linked to a prior run."""
        prior = self.run_store.get_run(prior_run_id)
        if not prior:
            raise ValueError(f"Prior run '{prior_run_id}' not found.")

        prior_req = SecurityReviewRequest.from_dict(prior.get("request", {}))
        diagnostics = prior.get("collector_diagnostics", {})

        target_collectors = list(prior_req.collector_ids)
        if only_failed and diagnostics:
            failed_ids = [
                cid for cid, diag in diagnostics.items()
                if diag.get("status") in (DiagnosticStatus.FAILED.value, DiagnosticStatus.PARTIAL.value)
            ]
            if failed_ids:
                target_collectors = failed_ids

        new_req_dict = prior_req.to_dict()
        new_req_dict["collector_ids"] = target_collectors
        new_req_dict["only_failed_collectors"] = only_failed
        new_req_dict["prior_run_id"] = prior_run_id

        return self.start_review(new_req_dict, async_run=async_run, owner_session_digest=owner_session_digest)

    def _execute_pipeline(
        self,
        run_id: str,
        req: SecurityReviewRequest,
        owner_session_digest: Optional[str] = None,
    ) -> SecurityReviewRun:
        """Executes the pipeline stages sequentially, respecting cancellation checkpoints."""
        logger.info("Executing security review pipeline for run %s", run_id)
        started_at = self.clock().isoformat()

        existing_run = self.run_store.get_run(run_id)
        created_at = (existing_run.get("created_at") if existing_run and isinstance(existing_run, dict) and existing_run.get("created_at") else None) or started_at

        run = SecurityReviewRun(
            run_id=run_id,
            request=req.to_dict(),
            state=RunState.RUNNING,
            stage="INITIALIZING",
            created_at=created_at,
            started_at=started_at,
            retry_of_run_id=req.prior_run_id,
        )
        self.run_store.save_run(run)
        self.job_manager.emit_event(
            run_id=run_id,
            event_type="run.started",
            data={"run_id": run_id, "started_at": started_at},
        )

        try:
            return self._run_pipeline_core(run, req, started_at, owner_session_digest=owner_session_digest)
        except Exception as unhandled:
            logger.error("Security review pipeline crashed for %s: %s", run_id, unhandled, exc_info=True)
            completed_at = self.clock().isoformat()
            run.state = RunState.FAILED
            run.stage = "FAILED"
            run.completed_at = completed_at
            run.failure_summary = f"Worker crash: {unhandled}"
            self.run_store.save_run(run)
            self.job_manager.emit_event(
                run_id=run_id,
                event_type="run.failed",
                data={"run_id": run_id, "error": str(unhandled), "completed_at": completed_at},
            )
            raise

    def _run_pipeline_core(
        self,
        run: SecurityReviewRun,
        req: SecurityReviewRequest,
        started_at: str,
        owner_session_digest: Optional[str] = None,
    ) -> SecurityReviewRun:
        run_id = run.run_id
        all_events: List[NormalizedSecurityEvent] = []
        collector_results: List[CollectorResult] = []
        collector_diagnostics: Dict[str, Dict[str, Any]] = {}
        successful_collectors = 0
        partial_collectors = 0
        failed_collectors = 0

        # Stage: COLLECTION
        run.stage = "COLLECTION"
        self.run_store.save_run(run)
        self.job_manager.emit_event(
            run_id=run_id,
            event_type="stage.started",
            data={"stage": "COLLECTION", "collectors": req.collector_ids},
        )

        hours_back = int(req.hours_back or 24)

        for col_id in req.collector_ids:
            # Checkpoint: cancellation
            if self.job_manager.is_cancelled(run_id):
                return self._finalize_cancellation(run, collector_diagnostics, all_events, collector_results)

            device_name = CANONICAL_COLLECTOR_MAP.get(col_id, col_id)
            self.job_manager.emit_event(
                run_id=run_id,
                event_type="collector.started",
                data={"collector_id": col_id, "device_name": device_name},
            )

            collector_req = CollectorRequest(
                start_time=req.start_time,
                end_time=req.end_time,
                hours_back=req.hours_back,
                max_records=req.max_records_per_collector or 500,
                mode=req.mode.value if hasattr(req.mode, "value") else str(req.mode),
                categories=req.categories,
                branches=req.branches,
                source_addresses=req.source_addresses,
                destination_addresses=req.destination_addresses,
                usernames=req.usernames,
                cancel_callback=lambda: self.job_manager.is_cancelled(run_id),
            )

            try:
                collector = self._get_collector_instance(col_id)
                try:
                    res: CollectorResult = collector.collect_logs(request=collector_req, hours_back=hours_back)
                except TypeError:
                    res: CollectorResult = collector.collect_logs(hours_back=hours_back)
            except Exception as exc:
                logger.error("Collector %s unhandled exception: %s", col_id, exc, exc_info=True)
                res = CollectorResult(
                    device_name=device_name,
                    status=CollectorStatus.FAILED,
                    error_message=str(exc),
                    events=[],
                    collection_duration_seconds=0.0,
                )

            collector_results.append(res)
            all_events.extend(res.events)

            # Map diagnostic and status counts
            if res.diagnostic is not None:
                diag = res.diagnostic
                diag_status_val = diag.status.value if hasattr(diag.status, "value") else str(diag.status)
                if diag_status_val == DiagnosticStatus.SUCCESS.value:
                    successful_collectors += 1
                elif diag_status_val == DiagnosticStatus.PARTIAL.value:
                    partial_collectors += 1
                elif diag_status_val != DiagnosticStatus.NOT_RUN.value:
                    failed_collectors += 1
            else:
                if res.status == CollectorStatus.SUCCESS:
                    diag_status = DiagnosticStatus.SUCCESS
                    diag_code = "OK"
                    diag_msg = f"Collected {len(res.events)} events in {res.collection_duration_seconds}s"
                    successful_collectors += 1
                elif res.status in (CollectorStatus.WARNING, CollectorStatus.PARTIAL):
                    diag_status = DiagnosticStatus.PARTIAL
                    diag_code = "WARNING"
                    diag_msg = res.error_message or "Partial collection completed"
                    partial_collectors += 1
                else:
                    diag_status = DiagnosticStatus.FAILED
                    diag_code = "COLLECTION_ERROR"
                    diag_msg = res.error_message or "Log collection failed"
                    failed_collectors += 1

                diag = CollectorDiagnostic(
                    collector_id=col_id,
                    device_name=res.device_name,
                    canonical_entity=col_id,
                    stage=DiagnosticStage.COMPLETE,
                    status=diag_status,
                    diagnostic_code=diag_code,
                    message=diag_msg,
                    requested_time_range={"hours_back": hours_back, "start": req.start_time, "end": req.end_time},
                    records_fetched=len(res.events),
                    records_parsed=len(res.events),
                    duration_seconds=res.collection_duration_seconds,
                )

            collector_diagnostics[col_id] = diag.to_dict()
            run.collector_diagnostics = collector_diagnostics

            self.job_manager.emit_event(
                run_id=run_id,
                event_type="collector.completed",
                data=diag.to_dict(),
            )

        # Checkpoint: cancellation
        if self.job_manager.is_cancelled(run_id):
            return self._finalize_cancellation(run, collector_diagnostics, all_events, collector_results)

        # Apply request filters to all_events if requested
        if req.source_addresses:
            src_set = set(req.source_addresses)
            all_events = [e for e in all_events if not e.attacker_ip or e.attacker_ip in src_set]
        if req.destination_addresses:
            dst_set = set(req.destination_addresses)
            all_events = [e for e in all_events if not e.target or e.target in dst_set]
        if req.usernames:
            user_set = set(req.usernames)
            all_events = [
                e for e in all_events
                if (e.target and e.target in user_set)
                or (isinstance(e.metadata, dict) and e.metadata.get("user") in user_set)
            ]
        if req.branches:
            branch_set = set(req.branches)
            all_events = [
                e for e in all_events
                if not (isinstance(e.metadata, dict) and e.metadata.get("branch"))
                or e.metadata.get("branch") in branch_set
            ]

        # Stage: CORRELATION
        run.stage = "CORRELATION"
        self.run_store.save_run(run)
        self.job_manager.emit_event(
            run_id=run_id,
            event_type="stage.started",
            data={"stage": "CORRELATION", "total_events": len(all_events)},
        )

        correlation_error: Optional[str] = None
        try:
            incidents: List[Incident] = self.risk_engine.process_events(all_events)
            for inc in incidents:
                attach_remediation_playbooks(inc)

            # Local attacker identity enrichment
            enrichment_cfg = self.config_mgr.get_identity_enrichment_config() if hasattr(self.config_mgr, "get_identity_enrichment_config") else {}
            if enrichment_cfg.get("enabled", True):
                for inc in incidents:
                    try:
                        self.identity_resolver.resolve_incident_identity(inc, events=all_events)
                    except Exception as res_err:
                        logger.warning("Identity resolution failed for incident %s (%s): %s", getattr(inc, "incident_id", "unknown"), getattr(inc, "attacker_ip", "none"), res_err)

            # Reconcile with persistent cross-run IncidentStore
            self.run_store.record_run_incidents(run_id, incidents)
        except Exception as exc:
            logger.error("Incident correlation or reconciliation failed for run %s: %s", run_id, exc, exc_info=True)
            incidents = []
            correlation_error = str(exc)
            run.warnings.append(f"Correlation error: {exc}")

        # Incident counts
        counts = {
            "total": len(incidents),
            "critical": sum(1 for i in incidents if i.severity == SeverityLevel.CRITICAL),
            "high": sum(1 for i in incidents if i.severity == SeverityLevel.HIGH),
            "medium": sum(1 for i in incidents if i.severity == SeverityLevel.MEDIUM),
            "low": sum(1 for i in incidents if i.severity == SeverityLevel.LOW),
            "info": sum(1 for i in incidents if i.severity == SeverityLevel.INFO),
        }
        run.incident_counts = counts

        # Checkpoint: cancellation
        if self.job_manager.is_cancelled(run_id):
            return self._finalize_cancellation(run, collector_diagnostics, all_events, collector_results, incidents)

        # Stage: PERSISTENCE
        run.stage = "PERSISTENCE"
        self.run_store.save_run(run)
        self.job_manager.emit_event(
            run_id=run_id,
            event_type="stage.started",
            data={"stage": "PERSISTENCE"},
        )

        serialized_events = [
            {
                "event_id": e.event_id,
                "timestamp": e.timestamp.isoformat() if hasattr(e.timestamp, "isoformat") else str(e.timestamp),
                "source_device": e.source_device,
                "category": e.category.value if hasattr(e.category, "value") else str(e.category),
                "threat_name": e.threat_name,
                "attacker_ip": e.attacker_ip,
                "target": e.target,
                "action_taken": e.action_taken,
                "count": e.count,
                "raw_snippet": e.raw_snippet,
                "metadata": e.metadata,
            }
            for e in all_events
        ]
        serialized_incidents = [
            {
                "incident_id": inc.incident_id,
                "display_id": inc.display_id or inc.incident_id,
                "fingerprint": inc.fingerprint,
                "title": inc.title,
                "severity": inc.severity.value if hasattr(inc.severity, "value") else str(inc.severity),
                "source_device": inc.source_device,
                "category": inc.category.value if hasattr(inc.category, "value") else str(inc.category),
                "signature_family": inc.signature_family,
                "first_seen": inc.first_seen.isoformat() if hasattr(inc.first_seen, "isoformat") else str(inc.first_seen),
                "last_seen": inc.last_seen.isoformat() if hasattr(inc.last_seen, "isoformat") else str(inc.last_seen),
                "description": inc.description,
                "action_taken": inc.action_taken,
                "event_count": inc.event_count,
                "attacker_ip": inc.attacker_ip,
                "target": inc.target,
                "lifecycle_state": inc.lifecycle_state,
                "occurrence_count": inc.occurrence_count,
                "devices_involved": inc.devices_involved,
                "branches_involved": inc.branches_involved,
                "affected_targets": inc.affected_targets,
                "observed_dispositions": inc.observed_dispositions,
                "supporting_event_ids": inc.supporting_event_ids,
                "distinct_signatures": inc.distinct_signatures,
                "blocked_count": inc.blocked_count,
                "allowed_count": inc.allowed_count,
                "severity_rationale": inc.severity_rationale,
                "remediation_cli": inc.remediation_cli,
                "remediation_gui": inc.remediation_gui,
                "remediation_mode_b_command": inc.remediation_mode_b_command,
                "attacker_pc_name": getattr(inc, "attacker_pc_name", None),
                "attacker_fqdn": getattr(inc, "attacker_fqdn", None),
                "attacker_username": getattr(inc, "attacker_username", None),
                "attacker_user_display_name": getattr(inc, "attacker_user_display_name", None),
                "attacker_device_owner": getattr(inc, "attacker_device_owner", None),
                "attacker_mac_address": getattr(inc, "attacker_mac_address", None),
                "attacker_network_scope": getattr(inc, "attacker_network_scope", None),
                "attacker_identity_status": getattr(inc, "attacker_identity_status", None),
                "attacker_identity_confidence": getattr(inc, "attacker_identity_confidence", None),
                "attacker_identity_confidence_score": getattr(inc, "attacker_identity_confidence_score", None),
                "attacker_identity_observed_at": getattr(inc, "attacker_identity_observed_at", None),
                "attacker_identity_sources": getattr(inc, "attacker_identity_sources", None),
                "attacker_identity_candidates": getattr(inc, "attacker_identity_candidates", None),
                "attacker_identity_diagnostics": getattr(inc, "attacker_identity_diagnostics", None),
                "attacker_attribution": getattr(inc, "attacker_attribution", None),
            }
            for inc in incidents
        ]

        self.run_store.save_events(run_id, serialized_events)
        self.run_store.save_incidents(run_id, serialized_incidents)
        self.run_store.save_collector_diagnostics(run_id, collector_diagnostics)

        # Checkpoint: cancellation
        if self.job_manager.is_cancelled(run_id):
            return self._finalize_cancellation(run, collector_diagnostics, all_events, collector_results, incidents)

        # Stage: ANALYSIS (if requested)
        analysis_engine_val = req.analysis_engine.value if hasattr(req.analysis_engine, "value") else str(req.analysis_engine or "NONE")
        if analysis_engine_val and analysis_engine_val.upper() != "NONE":
            run.stage = "ANALYSIS"
            self.run_store.save_run(run)
            self.job_manager.emit_event(
                run_id=run_id,
                event_type="stage.started",
                data={"stage": "ANALYSIS", "engine": analysis_engine_val, "model": req.analysis_model},
            )
            def _ai_progress_callback(evt_type: str, evt_data: Dict[str, Any]) -> None:
                self.job_manager.emit_event(
                    run_id=run_id,
                    event_type=f"analysis.{evt_type}",
                    data={"run_id": run_id, **evt_data},
                )

            try:
                analysis_out = self.ai_analyzer.analyze_run(
                    run_id=run_id,
                    engine=analysis_engine_val,
                    model=req.analysis_model,
                    owner_session_digest=owner_session_digest,
                    progress_callback=_ai_progress_callback,
                )
                if analysis_engine_val.upper() == "BOTH":
                    if analysis_out.get("codex", {}).get("analysis_id"):
                        run.analysis_refs.append(analysis_out["codex"]["analysis_id"])
                    if analysis_out.get("antigravity", {}).get("analysis_id"):
                        run.analysis_refs.append(analysis_out["antigravity"]["analysis_id"])
                    if analysis_out.get("analysis_id"):
                        run.analysis_refs.append(analysis_out["analysis_id"])
                elif analysis_out.get("analysis_id"):
                    run.analysis_refs.append(analysis_out["analysis_id"])
                self.run_store.save_run(run)
            except Exception as exc:
                logger.error("AI analysis stage failed for run %s: %s", run_id, exc, exc_info=True)
                run.warnings.append(f"AI analysis failed: {exc}")

        # Stage: REPORTING
        run.stage = "REPORTING"
        self.run_store.save_run(run)
        self.job_manager.emit_event(
            run_id=run_id,
            event_type="stage.started",
            data={"stage": "REPORTING", "formats": [f.value for f in req.report_formats]},
        )

        html_content = ""
        pdf_bytes = b""
        report_artifacts: Dict[str, Optional[str]] = {"html": None, "pdf": None, "json": None, "csv": None}

        try:
            # HTML
            if ReportFormat.HTML in req.report_formats or ReportFormat.PDF in req.report_formats:
                html_content = self.reporter.render_html_report(incidents=incidents, collectors=collector_results)
                html_path = self.run_store.save_report(run_id, "report.html", html_content)
                report_artifacts["html"] = str(html_path)

            # PDF
            if ReportFormat.PDF in req.report_formats:
                pdf_bytes = self.reporter.compile_pdf_report(
                    html_content=html_content, incidents=incidents, collectors=collector_results
                )
                pdf_path = self.run_store.save_report(run_id, "report.pdf", pdf_bytes)
                report_artifacts["pdf"] = str(pdf_path)

            # JSON
            if ReportFormat.JSON in req.report_formats:
                json_data = {
                    "run_id": run_id,
                    "counts": counts,
                    "incidents": serialized_incidents,
                    "collectors": collector_diagnostics,
                }
                json_path = self.run_store.save_report(run_id, "report.json", json.dumps(json_data, indent=2))
                report_artifacts["json"] = str(json_path)

            # CSV
            if ReportFormat.CSV in req.report_formats:
                csv_buf = io.StringIO()
                writer = csv.writer(csv_buf, lineterminator="\n")
                writer.writerow([
                    "incident_id", "severity", "category", "source_device",
                    "attacker_ip", "network_scope", "pc_name", "username",
                    "device_owner", "mac_address", "identity_status", "identity_confidence",
                    "identity_sources", "target", "title", "description",
                ])
                for inc in incidents:
                    id_sources = getattr(inc, "attacker_identity_sources", None)
                    sources_str = ", ".join(id_sources) if isinstance(id_sources, list) else (str(id_sources) if id_sources else "")
                    writer.writerow([
                        inc.incident_id,
                        inc.severity.value if hasattr(inc.severity, "value") else str(inc.severity),
                        inc.category.value if hasattr(inc.category, "value") else str(inc.category),
                        inc.source_device,
                        inc.attacker_ip or "",
                        getattr(inc, "attacker_network_scope", "") or "",
                        getattr(inc, "attacker_pc_name", "") or "",
                        getattr(inc, "attacker_username", "") or "",
                        getattr(inc, "attacker_device_owner", "") or "",
                        getattr(inc, "attacker_mac_address", "") or "",
                        getattr(inc, "attacker_identity_status", "") or "",
                        getattr(inc, "attacker_identity_confidence", "") or "",
                        sources_str,
                        inc.target or "",
                        inc.title,
                        inc.description,
                    ])
                csv_path = self.run_store.save_report(run_id, "report.csv", csv_buf.getvalue())
                report_artifacts["csv"] = str(csv_path)

            # Save legacy copy for existing downloader
            legacy_dir = Path(__file__).resolve().parent.parent.parent / "operations" / "reports"
            legacy_dir.mkdir(parents=True, exist_ok=True)
            today_str = self.clock().strftime("%Y%m%d")
            legacy_html = legacy_dir / f"MNE_Daily_Security_Report_{today_str}.html"
            legacy_pdf = legacy_dir / f"MNE_Daily_Security_Report_{today_str}.pdf"
            if html_content:
                with open(legacy_html, "w", encoding="utf-8") as f:
                    f.write(html_content)
            if pdf_bytes:
                with open(legacy_pdf, "wb") as f:
                    f.write(pdf_bytes)

        except Exception as exc:
            logger.error("Report generation error: %s", exc, exc_info=True)
            run.warnings.append(f"Report generation error: {exc}")

        run.report_artifacts = report_artifacts

        # Stage: EMAIL
        email_sent = False
        email_err: Optional[str] = None
        if req.send_email and html_content:
            run.stage = "EMAIL"
            self.run_store.save_run(run)
            recipients = req.recipients or self.config_mgr.get_recipients()
            self.job_manager.emit_event(
                run_id=run_id,
                event_type="stage.started",
                data={"stage": "EMAIL", "recipients": recipients},
            )
            try:
                email_sent = self.reporter.send_daily_security_email(
                    html_content=html_content,
                    pdf_bytes=pdf_bytes,
                    recipients=recipients,
                )
                if not email_sent:
                    email_err = "SMTP dispatch returned False."
            except Exception as exc:
                logger.error("Email dispatch failed: %s", exc, exc_info=True)
                email_err = str(exc)
                email_sent = False

            run.email_result = {
                "sent": email_sent,
                "recipients": recipients,
                "sent_at": self.clock().isoformat() if email_sent else None,
                "error": email_err,
            }
        else:
            run.email_result = {
                "sent": False,
                "recipients": [],
                "sent_at": None,
                "error": None if not req.send_email else "No report content to email.",
            }

        # Stage: FINALIZATION
        completed_at = self.clock().isoformat()
        run.completed_at = completed_at

        # Calculate final state
        if correlation_error:
            if successful_collectors > 0:
                run.state = RunState.PARTIAL
                run.stage = "COMPLETED_PARTIAL"
                if not run.failure_summary:
                    run.failure_summary = f"Completed with correlation error: {correlation_error}"
            else:
                run.state = RunState.FAILED
                run.stage = "FAILED"
                run.failure_summary = f"Failed with correlation error: {correlation_error}"
        elif successful_collectors == len(req.collector_ids) and (report_artifacts.get("html") or report_artifacts.get("pdf") or report_artifacts.get("json")):
            run.state = RunState.COMPLETED
            run.stage = "COMPLETED"
        elif (successful_collectors + partial_collectors) > 0:
            run.state = RunState.PARTIAL
            run.stage = "COMPLETED_PARTIAL"
        else:
            run.state = RunState.FAILED
            run.stage = "FAILED"
            run.failure_summary = "No requested collector produced usable data."

        self.run_store.save_run(run)

        # Record compatibility run result into SecurityAgentConfig
        legacy_summary = {
            "success": run.state in (RunState.COMPLETED, RunState.PARTIAL),
            "critical_count": counts["critical"],
            "high_count": counts["high"],
            "medium_count": counts["medium"],
            "total_incidents": counts["total"],
            "email_sent": email_sent,
            "html_path": report_artifacts.get("html"),
            "pdf_path": report_artifacts.get("pdf"),
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
        self.config_mgr.record_run_result(legacy_summary)

        self.job_manager.emit_event(
            run_id=run_id,
            event_type="run.completed" if run.state != RunState.FAILED else "run.failed",
            data={
                "run_id": run_id,
                "state": run.state.value,
                "incident_counts": counts,
                "completed_at": completed_at,
            },
        )
        logger.info("Security review pipeline finished for %s with state %s", run_id, run.state.value)
        return run

    def _finalize_cancellation(
        self,
        run: SecurityReviewRun,
        collector_diagnostics: Dict[str, Dict[str, Any]],
        all_events: List[NormalizedSecurityEvent],
        collector_results: List[CollectorResult],
        incidents: Optional[List[Incident]] = None,
    ) -> SecurityReviewRun:
        completed_at = self.clock().isoformat()
        run.state = RunState.CANCELLED
        run.stage = "CANCELLED"
        run.completed_at = completed_at
        run.collector_diagnostics = collector_diagnostics

        # Persist partial telemetry collected before cancellation
        if all_events:
            serialized_events = [
                {
                    "event_id": e.event_id,
                    "timestamp": e.timestamp.isoformat() if hasattr(e.timestamp, "isoformat") else str(e.timestamp),
                    "source_device": e.source_device,
                    "category": e.category.value if hasattr(e.category, "value") else str(e.category),
                    "threat_name": e.threat_name,
                    "attacker_ip": e.attacker_ip,
                    "target": e.target,
                    "action_taken": e.action_taken,
                    "count": e.count,
                    "raw_snippet": e.raw_snippet,
                    "metadata": e.metadata,
                }
                for e in all_events
            ]
            self.run_store.save_events(run.run_id, serialized_events)

        if collector_diagnostics:
            self.run_store.save_collector_diagnostics(run.run_id, collector_diagnostics)

        if incidents:
            serialized_incidents = [
                {
                    "incident_id": inc.incident_id,
                    "display_id": inc.display_id or inc.incident_id,
                    "fingerprint": inc.fingerprint,
                    "title": inc.title,
                    "severity": inc.severity.value if hasattr(inc.severity, "value") else str(inc.severity),
                    "source_device": inc.source_device,
                    "category": inc.category.value if hasattr(inc.category, "value") else str(inc.category),
                    "signature_family": inc.signature_family,
                    "first_seen": inc.first_seen.isoformat() if hasattr(inc.first_seen, "isoformat") else str(inc.first_seen),
                    "last_seen": inc.last_seen.isoformat() if hasattr(inc.last_seen, "isoformat") else str(inc.last_seen),
                    "description": inc.description,
                    "action_taken": inc.action_taken,
                    "event_count": inc.event_count,
                    "attacker_ip": inc.attacker_ip,
                    "target": inc.target,
                    "lifecycle_state": inc.lifecycle_state,
                    "occurrence_count": inc.occurrence_count,
                    "devices_involved": inc.devices_involved,
                    "branches_involved": inc.branches_involved,
                    "affected_targets": inc.affected_targets,
                    "observed_dispositions": inc.observed_dispositions,
                    "supporting_event_ids": inc.supporting_event_ids,
                    "distinct_signatures": inc.distinct_signatures,
                    "blocked_count": inc.blocked_count,
                    "allowed_count": inc.allowed_count,
                    "severity_rationale": inc.severity_rationale,
                    "remediation_cli": inc.remediation_cli,
                    "remediation_gui": inc.remediation_gui,
                    "remediation_mode_b_command": inc.remediation_mode_b_command,
                }
                for inc in incidents
            ]
            self.run_store.save_incidents(run.run_id, serialized_incidents)

        self.run_store.save_run(run)
        self.job_manager.emit_event(
            run_id=run.run_id,
            event_type="run.cancelled",
            data={"run_id": run.run_id, "completed_at": completed_at},
        )
        logger.info("Security review run %s was cancelled.", run.run_id)
        return run
