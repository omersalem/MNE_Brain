"""
Contracts and schema validation for MNE_Brain Release 2 Security Review Subsystem.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import jsonschema


SCHEMAS_DIR = Path(__file__).resolve().parent.parent.parent / "00_meta" / "schemas"


def _load_schema(schema_name: str) -> Dict[str, Any]:
    schema_path = SCHEMAS_DIR / schema_name
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    with open(schema_path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def validate_contract(data: Dict[str, Any], schema_name: str) -> None:
    """Validates a dictionary against a named JSON schema in 00_meta/schemas/."""
    schema = _load_schema(schema_name)
    validator = None
    try:
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT7
        registry = Registry()
        for f in SCHEMAS_DIR.glob("*.json"):
            try:
                s_data = json.loads(f.read_text(encoding="utf-8-sig"))
                res = Resource(contents=s_data, specification=DRAFT7)
                registry = registry.with_resource(uri=f.name, resource=res)
                if "$id" in s_data:
                    registry = registry.with_resource(uri=s_data["$id"], resource=res)
            except Exception:
                pass
        validator = jsonschema.Draft7Validator(schema=schema, registry=registry, format_checker=jsonschema.FormatChecker())
    except ImportError:
        pass

    if validator is not None:
        validator.validate(instance=data)
        return

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        resolver = jsonschema.RefResolver(base_uri=f"{SCHEMAS_DIR.as_uri()}/", referrer=schema)
        jsonschema.validate(instance=data, schema=schema, resolver=resolver, format_checker=jsonschema.FormatChecker())


class ReviewMode(str, Enum):
    QUICK = "QUICK"
    FULL = "FULL"
    DEEP = "DEEP"


class AnalysisEngine(str, Enum):
    NONE = "NONE"
    CODEX = "CODEX"
    ANTIGRAVITY = "ANTIGRAVITY"
    BOTH = "BOTH"


class ReportFormat(str, Enum):
    HTML = "HTML"
    PDF = "PDF"
    JSON = "JSON"
    CSV = "CSV"


class RunState(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class DiagnosticStage(str, Enum):
    CONNECTION = "CONNECTION"
    AUTHENTICATION = "AUTHENTICATION"
    QUERY = "QUERY"
    PARSE = "PARSE"
    COMPLETE = "COMPLETE"


class DiagnosticStatus(str, Enum):
    NOT_RUN = "NOT_RUN"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class IncidentLifecycleState(str, Enum):
    NEW = "NEW"
    RECURRING = "RECURRING"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    REOPENED = "REOPENED"


class AnalysisStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


@dataclass
class SecurityReviewRequest:
    mode: ReviewMode = ReviewMode.FULL
    collector_ids: List[str] = field(default_factory=lambda: [
        "fortigate_core",
        "fortianalyzer",
        "f5_bigip",
        "cisco_fmc",
        "sophos_email",
        "active_directory",
        "exchange_2019",
    ])
    hours_back: Optional[float] = 24.0
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    analysis_engine: AnalysisEngine = AnalysisEngine.NONE
    analysis_model: Optional[str] = None
    send_email: bool = True
    recipients: Optional[List[str]] = None
    report_formats: List[ReportFormat] = field(default_factory=lambda: [ReportFormat.HTML, ReportFormat.PDF])
    categories: Optional[List[str]] = None
    branches: Optional[List[str]] = None
    source_addresses: Optional[List[str]] = None
    destination_addresses: Optional[List[str]] = None
    usernames: Optional[List[str]] = None
    max_records_per_collector: Optional[int] = None
    only_failed_collectors: bool = False
    prior_run_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "mode": self.mode.value if isinstance(self.mode, ReviewMode) else str(self.mode),
            "collector_ids": list(self.collector_ids),
            "analysis_engine": self.analysis_engine.value if isinstance(self.analysis_engine, AnalysisEngine) else str(self.analysis_engine),
            "send_email": bool(self.send_email),
            "report_formats": [
                f.value if isinstance(f, ReportFormat) else str(f)
                for f in self.report_formats
            ],
            "only_failed_collectors": bool(self.only_failed_collectors),
        }
        if self.hours_back is not None:
            data["hours_back"] = float(self.hours_back)
        if self.start_time is not None:
            data["start_time"] = self.start_time
        if self.end_time is not None:
            data["end_time"] = self.end_time
        if self.analysis_model is not None:
            data["analysis_model"] = self.analysis_model
        if self.recipients is not None:
            data["recipients"] = list(self.recipients)
        if self.categories is not None:
            data["categories"] = list(self.categories)
        if self.branches is not None:
            data["branches"] = list(self.branches)
        if self.source_addresses is not None:
            data["source_addresses"] = list(self.source_addresses)
        if self.destination_addresses is not None:
            data["destination_addresses"] = list(self.destination_addresses)
        if self.usernames is not None:
            data["usernames"] = list(self.usernames)
        if self.max_records_per_collector is not None:
            data["max_records_per_collector"] = int(self.max_records_per_collector)
        if self.prior_run_id is not None:
            data["prior_run_id"] = self.prior_run_id
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SecurityReviewRequest:
        mode_val = data.get("mode", "FULL")
        mode = ReviewMode(mode_val) if isinstance(mode_val, str) and mode_val in ReviewMode.__members__ else ReviewMode.FULL
        
        engine_val = data.get("analysis_engine", "NONE")
        engine = AnalysisEngine(engine_val) if isinstance(engine_val, str) and engine_val in AnalysisEngine.__members__ else AnalysisEngine.NONE
        
        raw_formats = data.get("report_formats", ["HTML", "PDF"])
        formats = [
            ReportFormat(fmt) for fmt in raw_formats if isinstance(fmt, str) and fmt in ReportFormat.__members__
        ]
        if not formats:
            formats = [ReportFormat.HTML, ReportFormat.PDF]

        return cls(
            mode=mode,
            collector_ids=data.get("collector_ids", [
                "fortigate_core",
                "fortianalyzer",
                "f5_bigip",
                "cisco_fmc",
                "sophos_email",
                "active_directory",
                "exchange_2019",
            ]),
            hours_back=data.get("hours_back", 24.0) if "hours_back" in data else None,
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            analysis_engine=engine,
            analysis_model=data.get("analysis_model"),
            send_email=bool(data.get("send_email", True)),
            recipients=data.get("recipients"),
            report_formats=formats,
            categories=data.get("categories"),
            branches=data.get("branches"),
            source_addresses=data.get("source_addresses"),
            destination_addresses=data.get("destination_addresses"),
            usernames=data.get("usernames"),
            max_records_per_collector=data.get("max_records_per_collector"),
            only_failed_collectors=bool(data.get("only_failed_collectors", False)),
            prior_run_id=data.get("prior_run_id"),
        )

    def validate(self) -> None:
        validate_contract(self.to_dict(), "security-review-request.schema.json")


@dataclass
class CollectorDiagnostic:
    collector_id: str
    canonical_entity: str
    stage: DiagnosticStage = DiagnosticStage.COMPLETE
    status: DiagnosticStatus = DiagnosticStatus.NOT_RUN
    diagnostic_code: str = "PENDING"
    message: str = "Collector has not executed."
    device_name: Optional[str] = None
    requested_time_range: Optional[Dict[str, Any]] = None
    observed_time_range: Optional[Dict[str, Any]] = None
    transport: Optional[str] = None
    source_queried: Optional[str] = None
    records_fetched: int = 0
    records_parsed: int = 0
    records_ignored: int = 0
    records_malformed: int = 0
    records_duplicate: int = 0
    pagination: Optional[Dict[str, Any]] = None
    duration_seconds: float = 0.0
    suggested_next_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "collector_id": self.collector_id,
            "canonical_entity": self.canonical_entity,
            "stage": self.stage.value if isinstance(self.stage, DiagnosticStage) else str(self.stage),
            "status": self.status.value if isinstance(self.status, DiagnosticStatus) else str(self.status),
            "diagnostic_code": self.diagnostic_code,
            "message": self.message,
            "records_fetched": self.records_fetched,
            "records_parsed": self.records_parsed,
            "records_ignored": self.records_ignored,
            "records_malformed": self.records_malformed,
            "records_duplicate": self.records_duplicate,
            "duration_seconds": round(float(self.duration_seconds), 3),
        }
        if self.device_name:
            data["device_name"] = self.device_name
        if self.requested_time_range is not None:
            data["requested_time_range"] = self.requested_time_range
        if self.observed_time_range is not None:
            data["observed_time_range"] = self.observed_time_range
        if self.transport:
            data["transport"] = self.transport
        if self.source_queried:
            data["source_queried"] = self.source_queried
        if self.pagination is not None:
            data["pagination"] = self.pagination
        if self.suggested_next_action:
            data["suggested_next_action"] = self.suggested_next_action
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CollectorDiagnostic:
        stage_val = data.get("stage", "COMPLETE")
        stage = DiagnosticStage(stage_val) if isinstance(stage_val, str) and stage_val in DiagnosticStage.__members__ else DiagnosticStage.COMPLETE
        
        status_val = data.get("status", "NOT_RUN")
        status = DiagnosticStatus(status_val) if isinstance(status_val, str) and status_val in DiagnosticStatus.__members__ else DiagnosticStatus.NOT_RUN

        return cls(
            collector_id=data.get("collector_id", ""),
            canonical_entity=data.get("canonical_entity", ""),
            stage=stage,
            status=status,
            diagnostic_code=data.get("diagnostic_code", "UNKNOWN"),
            message=data.get("message", ""),
            device_name=data.get("device_name"),
            requested_time_range=data.get("requested_time_range"),
            observed_time_range=data.get("observed_time_range"),
            transport=data.get("transport"),
            source_queried=data.get("source_queried"),
            records_fetched=int(data.get("records_fetched", 0)),
            records_parsed=int(data.get("records_parsed", 0)),
            records_ignored=int(data.get("records_ignored", 0)),
            records_malformed=int(data.get("records_malformed", 0)),
            records_duplicate=int(data.get("records_duplicate", 0)),
            pagination=data.get("pagination"),
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            suggested_next_action=data.get("suggested_next_action"),
        )

    def validate(self) -> None:
        validate_contract(self.to_dict(), "security-collector-diagnostic.schema.json")


@dataclass
class SecurityReviewRun:
    run_id: str
    request: Dict[str, Any]
    state: RunState = RunState.QUEUED
    stage: str = "INITIALIZED"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    collector_diagnostics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    incident_counts: Dict[str, int] = field(default_factory=lambda: {
        "total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0
    })
    report_artifacts: Dict[str, Optional[str]] = field(default_factory=lambda: {
        "html": None, "pdf": None, "json": None, "csv": None
    })
    email_result: Optional[Dict[str, Any]] = None
    analysis_refs: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    failure_summary: Optional[str] = None
    retry_of_run_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "run_id": self.run_id,
            "request": self.request,
            "state": self.state.value if isinstance(self.state, RunState) else str(self.state),
            "stage": self.stage,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "collector_diagnostics": dict(self.collector_diagnostics),
            "incident_counts": dict(self.incident_counts),
            "report_artifacts": dict(self.report_artifacts),
            "email_result": self.email_result,
            "analysis_refs": list(self.analysis_refs),
            "warnings": list(self.warnings),
            "failure_summary": self.failure_summary,
            "retry_of_run_id": self.retry_of_run_id,
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SecurityReviewRun:
        state_val = data.get("state", "QUEUED")
        state = RunState(state_val) if isinstance(state_val, str) and state_val in RunState.__members__ else RunState.QUEUED

        return cls(
            run_id=data.get("run_id", ""),
            request=data.get("request", {}),
            state=state,
            stage=data.get("stage", "INITIALIZED"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            collector_diagnostics=data.get("collector_diagnostics", {}),
            incident_counts=data.get("incident_counts", {
                "total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0
            }),
            report_artifacts=data.get("report_artifacts", {
                "html": None, "pdf": None, "json": None, "csv": None
            }),
            email_result=data.get("email_result"),
            analysis_refs=data.get("analysis_refs", []),
            warnings=data.get("warnings", []),
            failure_summary=data.get("failure_summary"),
            retry_of_run_id=data.get("retry_of_run_id"),
        )

    def validate(self) -> None:
        validate_contract(self.to_dict(), "security-review-run.schema.json")
