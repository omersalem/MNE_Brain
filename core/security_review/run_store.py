"""
Persistent run storage for MNE_Brain Release 2 Security Review Subsystem.
Stores run metadata, events, diagnostics, incidents, and reports under operations/security_review/runs/<run_id>/
using atomic writes.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.security_review.contracts import SecurityReviewRun, validate_contract
from core.security_review.incidents import IncidentRecord, IncidentStore

logger = logging.getLogger(__name__)


class SecurityReviewRunStore:
    """Manages filesystem persistence of security review runs and cross-run incidents."""

    def __init__(self, base_dir: Optional[str | Path] = None):
        if base_dir is not None:
            self.base_dir = Path(base_dir).resolve()
        else:
            repo_root = Path(__file__).resolve().parent.parent.parent
            self.base_dir = repo_root / "operations" / "security_review" / "runs"

        if self.base_dir.name == "runs":
            inc_dir = self.base_dir.parent / "incidents"
            self.analyses_dir = self.base_dir.parent / "analyses"
        else:
            inc_dir = self.base_dir / "incidents"
            self.analyses_dir = self.base_dir / "analyses"
        self.incident_store = IncidentStore(inc_dir)

    def get_run_dir(self, run_id: str) -> Path:
        """Returns and ensures the directory for a specific run."""
        safe_id = "".join(c for c in run_id if c.isalnum() or c in ("-", "_")).strip()
        if not safe_id:
            raise ValueError(f"Invalid run_id '{run_id}'")
        run_dir = self.base_dir / safe_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "analyses").mkdir(exist_ok=True)
        (run_dir / "reports").mkdir(exist_ok=True)
        return run_dir

    def _atomic_write_json(self, path: Path, data: Any) -> None:
        """Writes JSON atomically to target path using a temp file with Windows lock-resilience."""
        path.parent.mkdir(parents=True, exist_ok=True)
        unique_id = uuid.uuid4().hex[:8]
        temp_path = path.with_name(f"{path.stem}_{unique_id}.tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # On Windows, os.replace can raise PermissionError if another thread has destination open.
            # Retry with short backoff.
            last_exc = None
            for attempt in range(10):
                try:
                    temp_path.replace(path)
                    return
                except (PermissionError, OSError) as exc:
                    last_exc = exc
                    time.sleep(0.03 * (attempt + 1))

            # Fallback: direct write if atomic replace is blocked by transient Windows read locks
            logger.warning("Atomic replace failed for %s, falling back to direct write: %s", path, last_exc)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink(missing_ok=True)
                except Exception:
                    pass

    def save_run(self, run: SecurityReviewRun | Dict[str, Any]) -> Dict[str, Any]:
        """Saves run metadata to run.json and request.json atomically."""
        run_dict = run.to_dict() if isinstance(run, SecurityReviewRun) else dict(run)
        run_id = run_dict["run_id"]
        run_dir = self.get_run_dir(run_id)

        # Validate against schema
        try:
            validate_contract(run_dict, "security-review-run.schema.json")
        except Exception as exc:
            logger.warning("Run schema validation warning for %s: %s", run_id, exc)

        # Save run.json
        self._atomic_write_json(run_dir / "run.json", run_dict)

        # Save request.json
        if "request" in run_dict and run_dict["request"]:
            self._atomic_write_json(run_dir / "request.json", run_dict["request"])

        return run_dict

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Loads run.json for a given run ID, or None if not found."""
        run_dir = self.base_dir / run_id
        run_file = run_dir / "run.json"
        if not run_file.exists():
            return None
        for attempt in range(5):
            try:
                with open(run_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (PermissionError, json.JSONDecodeError):
                time.sleep(0.02 * (attempt + 1))
            except Exception as exc:
                logger.error("Failed loading run %s: %s", run_id, exc)
                return None
        return None

    def save_collector_diagnostics(
        self, run_id: str, diagnostics: Dict[str, Any] | List[Dict[str, Any]]
    ) -> None:
        """Saves collector diagnostics to collector_diagnostics.json."""
        run_dir = self.get_run_dir(run_id)
        self._atomic_write_json(run_dir / "collector_diagnostics.json", diagnostics)

    def get_collector_diagnostics(self, run_id: str) -> Dict[str, Any] | List[Dict[str, Any]]:
        """Loads collector_diagnostics.json for a given run."""
        path = self.base_dir / run_id / "collector_diagnostics.json"
        if not path.exists():
            return {}
        for attempt in range(5):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (PermissionError, json.JSONDecodeError):
                time.sleep(0.02 * (attempt + 1))
            except Exception:
                return {}
        return {}

    def save_events(self, run_id: str, events: List[Dict[str, Any]]) -> None:
        """Saves normalized events to events.json."""
        run_dir = self.get_run_dir(run_id)
        self._atomic_write_json(run_dir / "events.json", events)

    def get_events(self, run_id: str) -> List[Dict[str, Any]]:
        """Loads events.json for a given run."""
        path = self.base_dir / run_id / "events.json"
        if not path.exists():
            return []
        for attempt in range(5):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (PermissionError, json.JSONDecodeError):
                time.sleep(0.02 * (attempt + 1))
            except Exception:
                return []
        return []

    def save_incidents(self, run_id: str, incidents: List[Dict[str, Any]]) -> None:
        """Saves consolidated incidents to incidents.json."""
        run_dir = self.get_run_dir(run_id)
        self._atomic_write_json(run_dir / "incidents.json", incidents)

    def get_incidents(self, run_id: str) -> List[Dict[str, Any]]:
        """Loads incidents.json for a given run."""
        path = self.base_dir / run_id / "incidents.json"
        if not path.exists():
            return []
        for attempt in range(5):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (PermissionError, json.JSONDecodeError):
                time.sleep(0.02 * (attempt + 1))
            except Exception:
                return []
        return []

    def save_report(self, run_id: str, filename: str, content: str | bytes) -> Path:
        """Saves a generated report file under reports/ in the run directory."""
        run_dir = self.get_run_dir(run_id)
        report_path = run_dir / "reports" / filename
        unique_id = uuid.uuid4().hex[:8]
        temp_path = report_path.with_name(f"{report_path.stem}_{unique_id}.tmp")
        try:
            if isinstance(content, str):
                with open(temp_path, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                with open(temp_path, "wb") as f:
                    f.write(content)
            for attempt in range(10):
                try:
                    temp_path.replace(report_path)
                    return report_path
                except (PermissionError, OSError):
                    time.sleep(0.03 * (attempt + 1))
            # Fallback direct write
            if isinstance(content, str):
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                with open(report_path, "wb") as f:
                    f.write(content)
            return report_path
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink(missing_ok=True)
                except Exception:
                    pass

    def get_report_path(self, run_id: str, filename: str) -> Optional[Path]:
        """Returns path to a report file if it exists."""
        p = self.base_dir / run_id / "reports" / filename
        return p if p.exists() else None

    def list_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Lists recent run summaries without loading full reports or large event files into memory."""
        summaries: List[Dict[str, Any]] = []
        if not self.base_dir.exists():
            return []

        for entry in self.base_dir.iterdir():
            if not entry.is_dir():
                continue
            run_file = entry / "run.json"
            if not run_file.exists():
                continue
            try:
                with open(run_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Create compact summary
                summaries.append({
                    "run_id": data.get("run_id", entry.name),
                    "state": data.get("state"),
                    "stage": data.get("stage"),
                    "created_at": data.get("created_at"),
                    "started_at": data.get("started_at"),
                    "completed_at": data.get("completed_at"),
                    "incident_counts": data.get("incident_counts", {}),
                    "collector_count": len(data.get("collector_diagnostics", {})),
                    "email_sent": (data.get("email_result") or {}).get("sent", False),
                    "reports": data.get("report_artifacts", {}),
                    "retry_of_run_id": data.get("retry_of_run_id"),
                })
            except Exception as exc:
                logger.debug("Error reading %s: %s", run_file, exc)
                continue

        # Sort descending by created_at
        summaries.sort(key=lambda s: s.get("created_at") or "", reverse=True)
        return summaries[:limit]

    def save_incident_record(self, record: IncidentRecord | Dict[str, Any]) -> IncidentRecord:
        return self.incident_store.save_incident(record)

    def get_incident_record(self, fingerprint: str) -> Optional[IncidentRecord]:
        return self.incident_store.get_incident(fingerprint)

    def list_incident_records(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        return self.incident_store.list_incidents(
            status=status,
            severity=severity,
            category=category,
            search=search,
            limit=limit,
            offset=offset,
        )

    def update_incident_status(
        self, fingerprint: str, new_status: str, author: str = "operator", note: str = ""
    ) -> Optional[Dict[str, Any]]:
        rec = self.incident_store.get_incident(fingerprint)
        if not rec:
            return None
        rec.update_status(new_status, author=author, note=note)
        saved = self.incident_store.save_incident(rec)
        return saved.to_dict()

    def add_incident_note(
        self, fingerprint: str, note: str, author: str = "operator"
    ) -> Optional[Dict[str, Any]]:
        rec = self.incident_store.get_incident(fingerprint)
        if not rec:
            return None
        rec.add_note(note, author=author)
        saved = self.incident_store.save_incident(rec)
        return saved.to_dict()

    def get_incident_timeline(self, fingerprint: str) -> List[Dict[str, Any]]:
        return self.incident_store.get_timeline(fingerprint)

    def record_run_incidents(self, run_id: str, incidents: List[Any]) -> List[IncidentRecord]:
        return self.incident_store.record_run_incidents(run_id, incidents)

    def update_incident_attribution(self, fingerprint: str, attribution: Dict[str, Any], author: str = "identity_resolver") -> Optional[Dict[str, Any]]:
        saved = self.incident_store.update_incident_attribution(fingerprint, attribution, author=author)
        return saved.to_dict() if saved else None

    def save_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Persists analysis result under runs/ or incidents/ and in shared analyses/."""
        analysis_id = str(analysis.get("analysis_id", "")).strip()
        if not analysis_id:
            raise ValueError("analysis_id is required")

        # Validate against schema
        try:
            validate_contract(analysis, "security-analysis-result.schema.json")
        except Exception as exc:
            logger.warning("Analysis result schema validation warning for %s: %s", analysis_id, exc)

        # 1. Save in shared analyses dir
        shared_path = self.analyses_dir / f"{analysis_id}.json"
        self._atomic_write_json(shared_path, analysis)

        # 2. Save under run directory if run_id present
        run_id = analysis.get("run_id")
        if run_id and run_id != "NONE" and run_id != "SELECTION":
            try:
                run_analyses_dir = self.get_run_dir(run_id) / "analyses"
                run_analyses_dir.mkdir(parents=True, exist_ok=True)
                self._atomic_write_json(run_analyses_dir / f"{analysis_id}.json", analysis)
            except Exception as exc:
                logger.debug("Failed saving analysis under run %s: %s", run_id, exc)

        # 3. Save under incident directory if fingerprint present
        fp = analysis.get("incident_fingerprint")
        if fp:
            try:
                inc_analyses_dir = self.incident_store.base_dir / fp / "analyses"
                inc_analyses_dir.mkdir(parents=True, exist_ok=True)
                self._atomic_write_json(inc_analyses_dir / f"{analysis_id}.json", analysis)
            except Exception as exc:
                logger.debug("Failed saving analysis under incident %s: %s", fp, exc)

        return analysis

    def get_analysis(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves analysis result by analysis_id."""
        safe_id = "".join(c for c in analysis_id if c.isalnum() or c in ("-", "_")).strip()
        if not safe_id:
            return None

        # Try shared dir first
        shared_path = self.analyses_dir / f"{safe_id}.json"
        if shared_path.exists():
            try:
                with open(shared_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                logger.error("Error reading analysis %s: %s", safe_id, exc)

        # Fallback search across runs
        if self.base_dir.exists():
            for run_dir in self.base_dir.iterdir():
                if not run_dir.is_dir():
                    continue
                cand = run_dir / "analyses" / f"{safe_id}.json"
                if cand.exists():
                    try:
                        with open(cand, "r", encoding="utf-8") as f:
                            return json.load(f)
                    except Exception:
                        pass

        return None

    def list_analyses(
        self, run_id: Optional[str] = None, fingerprint: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Lists recent analyses filtered optionally by run_id or incident fingerprint."""
        results: List[Dict[str, Any]] = []
        if not self.analyses_dir.exists():
            return results

        for p in self.analyses_dir.glob("*.json"):
            if p.stem == "index":
                continue
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if run_id and data.get("run_id") != run_id:
                    continue
                if fingerprint and data.get("incident_fingerprint") != fingerprint:
                    continue
                results.append(data)
            except Exception:
                continue

        results.sort(key=lambda a: a.get("created_at") or "", reverse=True)
        return results[:limit]

    def save_comparison(self, comparison: Dict[str, Any]) -> Dict[str, Any]:
        cmp_id = str(comparison.get("comparison_id", "")).strip()
        if not cmp_id:
            raise ValueError("comparison_id is required")
        cmp_dir = self.analyses_dir / "comparisons"
        cmp_dir.mkdir(parents=True, exist_ok=True)
        self._atomic_write_json(cmp_dir / f"{cmp_id}.json", comparison)
        return comparison

    def get_comparison(self, comparison_id: str) -> Optional[Dict[str, Any]]:
        safe_id = "".join(c for c in comparison_id if c.isalnum() or c in ("-", "_")).strip()
        p = self.analyses_dir / "comparisons" / f"{safe_id}.json"
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None
