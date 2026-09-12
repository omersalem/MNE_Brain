"""
Incident lifecycle management and persistent cross-run incident store for MNE_Brain Release 2.
Adheres strictly to 00_meta/schemas/security-incident-record.schema.json.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.connectors.security.models import Incident, SeverityLevel, ThreatCategory, normalize_action
from core.security_review.contracts import validate_contract
from core.security_review.identity_enrichment import AttackerAttribution, should_replace_attribution

logger = logging.getLogger(__name__)

SEVERITY_WEIGHT = {
    "CRITICAL": 5,
    "HIGH": 4,
    "MEDIUM": 3,
    "LOW": 2,
    "INFO": 1,
}


class IncidentLifecycleState(str, Enum):
    NEW = "NEW"
    RECURRING = "RECURRING"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    REOPENED = "REOPENED"


def generate_fingerprint(
    category: str,
    signature_family: str,
    source_scope: str,
    attacker_identity: str,
    target_identity: str,
    branch_scope: str = "",
) -> str:
    """Generates a stable, deterministic fingerprint string for cross-run tracking.
    Guarantees that different exploit signatures or targets are not merged
    merely because an IP matches.
    """
    cat = (category or "").strip().upper()
    sig = (signature_family or "generic").strip().lower()
    scope = (source_scope or "appliance").strip().lower()
    attacker = (attacker_identity or "none").strip().lower()
    target = (target_identity or "perimeter").strip().lower()
    branch = (branch_scope or "core").strip().lower()

    canonical_str = f"{cat}|{sig}|{scope}|{attacker}|{target}|{branch}"
    digest = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()[:16]
    return f"inc-{digest}"


@dataclass
class IncidentRecord:
    """Security incident record adhering to security-incident-record.schema.json."""
    fingerprint: str
    display_id: str
    title: str
    category: str
    signature_family: str
    source_device: str = ""
    source_entity: str = ""
    attacker_identity: str = ""
    target_identity: str = ""
    branch: str = ""
    lifecycle_state: str = "NEW"
    first_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    occurrence_count: int = 1
    run_references: List[str] = field(default_factory=list)
    peak_severity: str = "MEDIUM"
    current_severity: str = "MEDIUM"
    description: str = ""
    action_taken: str = "UNKNOWN"
    event_count: int = 1
    analyst_notes: List[Dict[str, str]] = field(default_factory=list)
    linked_conversation_thread_id: Optional[str] = None
    linked_p8_session_id: Optional[str] = None
    linked_p9_session_id: Optional[str] = None
    analysis_references: List[str] = field(default_factory=list)
    remediation_cli: List[str] = field(default_factory=list)
    remediation_gui: List[str] = field(default_factory=list)
    remediation_mode_b_command: Optional[str] = None
    attacker_pc_name: str = "Unknown"
    attacker_fqdn: str = "Unknown"
    attacker_username: str = "Unknown"
    attacker_user_display_name: str = "Unknown"
    attacker_device_owner: str = "Unknown"
    attacker_primary_device_user: str = "Unknown"
    attacker_claimed_username: str = "Unknown"
    attacker_target_account: str = "Unknown"
    attacker_mac_address: str = "Unknown"
    attacker_network_scope: str = "UNKNOWN"
    attacker_identity_status: str = "NOT_CONFIGURED"
    attacker_identity_confidence: str = "UNKNOWN"
    attacker_identity_confidence_score: int = 0
    attacker_identity_observed_at: Optional[str] = None
    attacker_identity_sources: List[str] = field(default_factory=list)
    attacker_identity_candidates: List[Dict[str, Any]] = field(default_factory=list)
    attacker_identity_diagnostics: List[str] = field(default_factory=list)
    supporting_event_ids: List[str] = field(default_factory=list)
    attacker_attribution: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes strictly into the schema-conforming dictionary."""
        data = {
            "fingerprint": self.fingerprint,
            "display_id": self.display_id,
            "title": self.title,
            "category": self.category,
            "signature_family": self.signature_family,
            "source_device": self.source_device,
            "source_entity": self.source_entity,
            "attacker_identity": self.attacker_identity,
            "target_identity": self.target_identity,
            "branch": self.branch,
            "lifecycle_state": self.lifecycle_state,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "occurrence_count": max(1, self.occurrence_count),
            "run_references": list(self.run_references),
            "peak_severity": self.peak_severity,
            "current_severity": self.current_severity,
            "description": self.description,
            "action_taken": self.action_taken,
            "event_count": max(1, self.event_count),
            "analyst_notes": [
                {
                    "timestamp": n.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "author": n.get("author", "operator"),
                    "note": n.get("note", ""),
                }
                for n in self.analyst_notes
            ],
            "linked_conversation_thread_id": self.linked_conversation_thread_id,
            "linked_p8_session_id": self.linked_p8_session_id,
            "linked_p9_session_id": self.linked_p9_session_id,
            "analysis_references": list(self.analysis_references),
            "remediation_cli": list(self.remediation_cli),
            "remediation_gui": list(self.remediation_gui),
            "remediation_mode_b_command": self.remediation_mode_b_command,
            "attacker_pc_name": self.attacker_pc_name,
            "attacker_fqdn": self.attacker_fqdn,
            "attacker_username": self.attacker_username,
            "attacker_user_display_name": self.attacker_user_display_name,
            "attacker_device_owner": self.attacker_device_owner,
            "attacker_primary_device_user": self.attacker_primary_device_user,
            "attacker_claimed_username": self.attacker_claimed_username,
            "attacker_target_account": self.attacker_target_account,
            "attacker_mac_address": self.attacker_mac_address,
            "attacker_network_scope": self.attacker_network_scope,
            "attacker_identity_status": self.attacker_identity_status,
            "attacker_identity_confidence": self.attacker_identity_confidence,
            "attacker_identity_confidence_score": self.attacker_identity_confidence_score,
            "attacker_identity_observed_at": self.attacker_identity_observed_at,
            "attacker_identity_sources": list(self.attacker_identity_sources),
            "attacker_identity_candidates": list(self.attacker_identity_candidates),
            "attacker_identity_diagnostics": list(self.attacker_identity_diagnostics),
            "supporting_event_ids": list(self.supporting_event_ids),
            "attacker_attribution": dict(self.attacker_attribution) if self.attacker_attribution else None,
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> IncidentRecord:
        return cls(
            fingerprint=data.get("fingerprint", ""),
            display_id=data.get("display_id", ""),
            title=data.get("title", ""),
            category=data.get("category", ""),
            signature_family=data.get("signature_family", ""),
            source_device=data.get("source_device", ""),
            source_entity=data.get("source_entity", ""),
            attacker_identity=data.get("attacker_identity", ""),
            target_identity=data.get("target_identity", ""),
            branch=data.get("branch", ""),
            lifecycle_state=data.get("lifecycle_state", "NEW"),
            first_seen=data.get("first_seen", datetime.now(timezone.utc).isoformat()),
            last_seen=data.get("last_seen", datetime.now(timezone.utc).isoformat()),
            occurrence_count=data.get("occurrence_count", 1),
            run_references=list(data.get("run_references", [])),
            peak_severity=data.get("peak_severity", "MEDIUM"),
            current_severity=data.get("current_severity", "MEDIUM"),
            description=data.get("description", ""),
            action_taken=data.get("action_taken", "UNKNOWN"),
            event_count=data.get("event_count", 1),
            analyst_notes=list(data.get("analyst_notes", [])),
            linked_conversation_thread_id=data.get("linked_conversation_thread_id"),
            linked_p8_session_id=data.get("linked_p8_session_id"),
            linked_p9_session_id=data.get("linked_p9_session_id"),
            analysis_references=list(data.get("analysis_references", [])),
            remediation_cli=list(data.get("remediation_cli", [])),
            remediation_gui=list(data.get("remediation_gui", [])),
            remediation_mode_b_command=data.get("remediation_mode_b_command"),
            attacker_pc_name=data.get("attacker_pc_name", "Unknown"),
            attacker_fqdn=data.get("attacker_fqdn", "Unknown"),
            attacker_username=data.get("attacker_username", "Unknown"),
            attacker_user_display_name=data.get("attacker_user_display_name", "Unknown"),
            attacker_device_owner=data.get("attacker_device_owner", "Unknown"),
            attacker_primary_device_user=data.get("attacker_primary_device_user", "Unknown"),
            attacker_claimed_username=data.get("attacker_claimed_username", "Unknown"),
            attacker_target_account=data.get("attacker_target_account", "Unknown"),
            attacker_mac_address=data.get("attacker_mac_address", "Unknown"),
            attacker_network_scope=data.get("attacker_network_scope", "UNKNOWN"),
            attacker_identity_status=data.get("attacker_identity_status", "NOT_CONFIGURED"),
            attacker_identity_confidence=data.get("attacker_identity_confidence", "UNKNOWN"),
            attacker_identity_confidence_score=data.get("attacker_identity_confidence_score", 0),
            attacker_identity_observed_at=data.get("attacker_identity_observed_at"),
            attacker_identity_sources=list(data.get("attacker_identity_sources", [])),
            attacker_identity_candidates=list(data.get("attacker_identity_candidates", [])),
            attacker_identity_diagnostics=list(data.get("attacker_identity_diagnostics", [])),
            supporting_event_ids=list(data.get("supporting_event_ids", [])),
            attacker_attribution=data.get("attacker_attribution"),
        )


    def validate(self) -> None:
        validate_contract(self.to_dict(), "security-incident-record.schema.json")

    def update_status(self, new_status: str, author: str = "operator", note: str = "") -> None:
        status_upper = new_status.strip().upper()
        if status_upper not in IncidentLifecycleState.__members__:
            raise ValueError(f"Invalid lifecycle state '{new_status}'. Allowed: {list(IncidentLifecycleState.__members__.keys())}")
        old_status = self.lifecycle_state
        self.lifecycle_state = status_upper
        now_iso = datetime.now(timezone.utc).isoformat()
        auto_note = f"Status changed from {old_status} to {status_upper}"
        if note:
            auto_note += f": {note}"
        self.analyst_notes.append({
            "timestamp": now_iso,
            "author": author,
            "note": auto_note,
        })

    def add_note(self, note: str, author: str = "operator") -> None:
        if not note or not note.strip():
            raise ValueError("Note content cannot be empty.")
        now_iso = datetime.now(timezone.utc).isoformat()
        self.analyst_notes.append({
            "timestamp": now_iso,
            "author": author or "operator",
            "note": note.strip(),
        })


class IncidentStore:
    """Persistent storage and indexing for cross-run security incidents under operations/security_review/incidents/."""

    def __init__(self, base_dir: Optional[str | Path] = None):
        if base_dir is not None:
            self.base_dir = Path(base_dir).resolve()
        else:
            repo_root = Path(__file__).resolve().parent.parent.parent
            self.base_dir = repo_root / "operations" / "security_review" / "incidents"
        self.index_file = self.base_dir / "index.json"

    def _ensure_index(self) -> None:
        if not self.index_file.exists():
            self._rebuild_index()

    def _atomic_write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        unique_id = uuid.uuid4().hex[:8]
        temp_path = path.with_name(f"{path.stem}_{unique_id}.tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            for attempt in range(10):
                try:
                    temp_path.replace(path)
                    return
                except (PermissionError, OSError):
                    time.sleep(0.03 * (attempt + 1))
            # Fallback: direct write
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink(missing_ok=True)
                except Exception:
                    pass

    def _rebuild_index(self) -> None:
        """Rebuilds compact index from all incident files."""
        if not self.base_dir.exists():
            return
        summaries: Dict[str, Dict[str, Any]] = {}
        for entry in self.base_dir.glob("inc-*.json"):
            try:
                with open(entry, "r", encoding="utf-8") as f:
                    rec = json.load(f)
                fp = rec.get("fingerprint")
                if fp:
                    summaries[fp] = self._make_summary(rec)
            except Exception as exc:
                logger.debug("Error indexing %s: %s", entry, exc)
        self._atomic_write_json(self.index_file, summaries)

    def _make_summary(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "fingerprint": rec.get("fingerprint"),
            "display_id": rec.get("display_id"),
            "title": rec.get("title"),
            "category": rec.get("category"),
            "signature_family": rec.get("signature_family"),
            "current_severity": rec.get("current_severity"),
            "peak_severity": rec.get("peak_severity"),
            "lifecycle_state": rec.get("lifecycle_state"),
            "first_seen": rec.get("first_seen"),
            "last_seen": rec.get("last_seen"),
            "occurrence_count": rec.get("occurrence_count", 1),
            "event_count": rec.get("event_count", 1),
            "source_device": rec.get("source_device"),
            "attacker_identity": rec.get("attacker_identity"),
            "target_identity": rec.get("target_identity"),
            "branch": rec.get("branch"),
            "action_taken": rec.get("action_taken"),
            "run_references": rec.get("run_references", []),
            "attacker_pc_name": rec.get("attacker_pc_name", "Unknown"),
            "attacker_fqdn": rec.get("attacker_fqdn", "Unknown"),
            "attacker_username": rec.get("attacker_username", "Unknown"),
            "attacker_device_owner": rec.get("attacker_device_owner", "Unknown"),
            "attacker_mac_address": rec.get("attacker_mac_address", "Unknown"),
            "attacker_network_scope": rec.get("attacker_network_scope", "UNKNOWN"),
            "attacker_identity_status": rec.get("attacker_identity_status", "NOT_CONFIGURED"),
            "attacker_identity_confidence": rec.get("attacker_identity_confidence", "UNKNOWN"),
            "attacker_identity_confidence_score": rec.get("attacker_identity_confidence_score", 0),
            "attacker_identity_sources": rec.get("attacker_identity_sources", []),
        }

    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        if not self.base_dir.exists():
            return {}
        try:
            if self.index_file.exists():
                with open(self.index_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as exc:
            logger.warning("Failed reading incident index, rebuilding: %s", exc)
        self._rebuild_index()
        try:
            if self.index_file.exists():
                with open(self.index_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            return {}
        return {}

    def save_incident(self, record: IncidentRecord | Dict[str, Any]) -> IncidentRecord:
        """Atomically saves an incident record and updates the compact index."""
        rec_obj = record if isinstance(record, IncidentRecord) else IncidentRecord.from_dict(record)
        rec_obj.validate()

        rec_dict = rec_obj.to_dict()
        file_path = self.base_dir / f"{rec_obj.fingerprint}.json"
        self._atomic_write_json(file_path, rec_dict)

        # Update index
        index = self._load_index()
        index[rec_obj.fingerprint] = self._make_summary(rec_dict)
        self._atomic_write_json(self.index_file, index)

        return rec_obj

    def get_incident(self, fingerprint: str) -> Optional[IncidentRecord]:
        """Loads full incident record by fingerprint."""
        safe_fp = "".join(c for c in fingerprint if c.isalnum() or c in ("-", "_")).strip()
        if not safe_fp:
            return None
        file_path = self.base_dir / f"{safe_fp}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return IncidentRecord.from_dict(data)
        except Exception as exc:
            logger.error("Failed loading incident %s: %s", safe_fp, exc)
            return None

    def list_incidents(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Queries incidents using the compact index without loading full event blobs."""
        index = self._load_index()
        items = list(index.values())

        if status and status.upper() != "ALL":
            st_up = status.upper()
            items = [i for i in items if i.get("lifecycle_state") == st_up]

        if severity and severity.upper() != "ALL":
            sev_up = severity.upper()
            items = [i for i in items if i.get("current_severity") == sev_up]

        if category and category.upper() != "ALL":
            cat_up = category.upper()
            items = [i for i in items if (i.get("category") or "").upper() == cat_up]

        if search and search.strip():
            term = search.strip().lower()
            items = [
                i for i in items
                if term in (i.get("title") or "").lower()
                or term in (i.get("fingerprint") or "").lower()
                or term in (i.get("display_id") or "").lower()
                or term in (i.get("attacker_identity") or "").lower()
                or term in (i.get("target_identity") or "").lower()
                or term in (i.get("source_device") or "").lower()
                or term in (i.get("attacker_pc_name") or "").lower()
                or term in (i.get("attacker_fqdn") or "").lower()
                or term in (i.get("attacker_username") or "").lower()
                or term in (i.get("attacker_device_owner") or "").lower()
                or term in (i.get("attacker_mac_address") or "").lower()
            ]

        # Sort: first by current_severity weight desc, then last_seen desc
        def sort_key(item: Dict[str, Any]):
            weight = SEVERITY_WEIGHT.get(item.get("current_severity", "INFO"), 0)
            last_seen = item.get("last_seen") or ""
            return (-weight, last_seen)

        items.sort(key=sort_key)
        total = len(items)
        page = items[offset : offset + limit]
        return page, total

    def record_run_incidents(self, run_id: str, incidents: List[Incident]) -> List[IncidentRecord]:
        """Reconciles incidents from a run against the persistent incident store.
        - Existing incidents have their occurrence count incremented, last_seen updated,
          and lifecycle states adjusted (e.g. RESOLVED -> REOPENED, NEW -> RECURRING).
        - New incidents are assigned lifecycle_state=NEW and persisted.
        """
        records: List[IncidentRecord] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for inc in incidents:
            fp = inc.fingerprint
            if not fp:
                # Should already have fingerprint from risk engine
                fp = generate_fingerprint(
                    category=inc.category.value if hasattr(inc.category, "value") else str(inc.category),
                    signature_family=inc.signature_family or inc.title,
                    source_scope=inc.source_device,
                    attacker_identity=inc.attacker_ip or "",
                    target_identity=inc.target or "",
                    branch_scope=",".join(inc.branches_involved) if inc.branches_involved else "",
                )
                inc.fingerprint = fp

            existing = self.get_incident(fp)
            first_seen_iso = inc.first_seen.isoformat() if hasattr(inc.first_seen, "isoformat") else str(inc.first_seen)
            last_seen_iso = inc.last_seen.isoformat() if hasattr(inc.last_seen, "isoformat") else str(inc.last_seen)
            curr_sev = inc.severity.value if hasattr(inc.severity, "value") else str(inc.severity)

            if existing:
                existing.occurrence_count += 1
                if run_id and run_id not in existing.run_references:
                    existing.run_references.append(run_id)
                existing.last_seen = last_seen_iso
                existing.event_count += inc.event_count
                existing.current_severity = curr_sev

                # Peak severity calculation
                if SEVERITY_WEIGHT.get(curr_sev, 0) > SEVERITY_WEIGHT.get(existing.peak_severity, 0):
                    existing.peak_severity = curr_sev

                # Action and description update
                if inc.action_taken:
                    existing.action_taken = inc.action_taken
                if inc.description:
                    existing.description = inc.description

                # Playbook updates
                if inc.remediation_cli:
                    existing.remediation_cli = inc.remediation_cli
                if inc.remediation_gui:
                    existing.remediation_gui = inc.remediation_gui
                if inc.remediation_mode_b_command:
                    existing.remediation_mode_b_command = inc.remediation_mode_b_command

                # Non-downgrade Identity attribution updates
                existing_attr = None
                if existing.attacker_attribution:
                    existing_attr = AttackerAttribution.from_dict(existing.attacker_attribution)
                elif existing.attacker_identity_status:
                    existing_attr = AttackerAttribution(
                        ip_address=existing.attacker_identity,
                        network_scope=existing.attacker_network_scope or "UNKNOWN",
                        pc_name=existing.attacker_pc_name or "Unknown",
                        fqdn=existing.attacker_fqdn or "Unknown",
                        username=existing.attacker_username or "Unknown",
                        status=existing.attacker_identity_status or "NOT_CONFIGURED",
                        confidence=existing.attacker_identity_confidence or "UNKNOWN",
                        confidence_score=existing.attacker_identity_confidence_score or 0,
                    )

                new_attr = None
                if getattr(inc, "attacker_attribution", None):
                    new_attr = AttackerAttribution.from_dict(inc.attacker_attribution)
                elif getattr(inc, "attacker_identity_status", None):
                    new_attr = AttackerAttribution(
                        ip_address=getattr(inc, "attacker_identity", "") or existing.attacker_identity,
                        network_scope=getattr(inc, "attacker_network_scope", "UNKNOWN"),
                        pc_name=getattr(inc, "attacker_pc_name", "Unknown"),
                        fqdn=getattr(inc, "attacker_fqdn", "Unknown"),
                        username=getattr(inc, "attacker_username", "Unknown"),
                        status=getattr(inc, "attacker_identity_status", "NOT_CONFIGURED"),
                        confidence=getattr(inc, "attacker_identity_confidence", "UNKNOWN"),
                        confidence_score=getattr(inc, "attacker_identity_confidence_score", 0),
                    )

                if new_attr is not None:
                    should_replace = True
                    if existing_attr and new_attr:
                        should_replace = should_replace_attribution(existing_attr, new_attr)

                    inc_time_raw = getattr(inc, "last_seen", None)
                    if isinstance(inc_time_raw, datetime):
                        inc_time = inc_time_raw.isoformat()
                    elif isinstance(inc_time_raw, str) and inc_time_raw.strip():
                        inc_time = inc_time_raw.strip()
                    else:
                        inc_time = now_iso

                    conf_val = new_attr.confidence if new_attr.confidence in ("HIGH", "MEDIUM", "LOW", "UNKNOWN") else "UNKNOWN"
                    attempt_entry = {
                        "run_id": run_id,
                        "incident_time": inc_time,
                        "attempt_time": now_iso,
                        "status": new_attr.status,
                        "confidence": conf_val,
                        "confidence_score": int(new_attr.confidence_score or 0),
                        "pc_name": new_attr.pc_name if new_attr.pc_name not in ("Unknown", "Not applicable") else None,
                        "username": new_attr.username if new_attr.username not in ("Unknown", "Not applicable") else None,
                        "sources": list(new_attr.successful_sources),
                        "diagnostic": f"Attempt in run {run_id}: {'Accepted' if should_replace else 'Preserved prior higher-confidence attribution'}",
                    }

                    if should_replace:
                        existing.attacker_pc_name = new_attr.pc_name
                        existing.attacker_fqdn = new_attr.fqdn
                        existing.attacker_username = new_attr.username
                        existing.attacker_user_display_name = new_attr.user_display_name
                        existing.attacker_device_owner = new_attr.device_owner
                        existing.attacker_mac_address = new_attr.mac_address
                        existing.attacker_network_scope = new_attr.network_scope
                        existing.attacker_identity_status = new_attr.status
                        existing.attacker_identity_confidence = new_attr.confidence
                        existing.attacker_identity_confidence_score = new_attr.confidence_score
                        existing.attacker_identity_observed_at = new_attr.observed_at
                        existing.attacker_identity_sources = list(new_attr.successful_sources)
                        existing.attacker_identity_candidates = list(new_attr.candidates)
                        existing.attacker_identity_diagnostics = list(new_attr.diagnostics)

                        history = list(getattr(existing_attr, "attribution_history", [])) if existing_attr else []
                        history.append(attempt_entry)
                        if len(history) > 10:
                            history = history[-10:]
                        new_attr.attribution_history = history
                        existing.attacker_attribution = new_attr.to_dict()
                    elif existing_attr:
                        history = list(getattr(existing_attr, "attribution_history", []))
                        history.append(attempt_entry)
                        if len(history) > 10:
                            history = history[-10:]
                        existing_attr.attribution_history = history
                        existing.attacker_attribution = existing_attr.to_dict()

                # Merge supporting_event_ids without duplicates
                new_supp = getattr(inc, "supporting_event_ids", []) or []
                if new_supp:
                    existing.supporting_event_ids = list(dict.fromkeys(existing.supporting_event_ids + new_supp))

                # Lifecycle state transition
                if existing.lifecycle_state == IncidentLifecycleState.RESOLVED.value:
                    existing.lifecycle_state = IncidentLifecycleState.REOPENED.value
                    existing.analyst_notes.append({
                        "timestamp": now_iso,
                        "author": "system",
                        "note": f"Incident re-detected in run {run_id}; automatically reopened from RESOLVED.",
                    })
                elif existing.lifecycle_state == IncidentLifecycleState.NEW.value:
                    existing.lifecycle_state = IncidentLifecycleState.RECURRING.value

                # Keep display_id aligned with latest run if desired or retain original
                inc.lifecycle_state = existing.lifecycle_state
                inc.occurrence_count = existing.occurrence_count

                saved = self.save_incident(existing)
                records.append(saved)
            else:
                new_record = IncidentRecord(
                    fingerprint=fp,
                    display_id=inc.incident_id or inc.display_id,
                    title=inc.title,
                    category=inc.category.value if hasattr(inc.category, "value") else str(inc.category),
                    signature_family=inc.signature_family or inc.title,
                    source_device=inc.source_device,
                    source_entity=inc.source_device,
                    attacker_identity=inc.attacker_ip or "",
                    target_identity=inc.target or "",
                    branch=",".join(inc.branches_involved) if inc.branches_involved else "",
                    lifecycle_state=IncidentLifecycleState.NEW.value,
                    first_seen=first_seen_iso,
                    last_seen=last_seen_iso,
                    occurrence_count=1,
                    run_references=[run_id] if run_id else [],
                    peak_severity=curr_sev,
                    current_severity=curr_sev,
                    description=inc.description,
                    action_taken=inc.action_taken,
                    event_count=inc.event_count,
                    analyst_notes=[],
                    remediation_cli=inc.remediation_cli,
                    remediation_gui=inc.remediation_gui,
                    remediation_mode_b_command=inc.remediation_mode_b_command,
                    attacker_pc_name=getattr(inc, "attacker_pc_name", "Unknown"),
                    attacker_fqdn=getattr(inc, "attacker_fqdn", "Unknown"),
                    attacker_username=getattr(inc, "attacker_username", "Unknown"),
                    attacker_user_display_name=getattr(inc, "attacker_user_display_name", "Unknown"),
                    attacker_device_owner=getattr(inc, "attacker_device_owner", "Unknown"),
                    attacker_mac_address=getattr(inc, "attacker_mac_address", "Unknown"),
                    attacker_network_scope=getattr(inc, "attacker_network_scope", "UNKNOWN"),
                    attacker_identity_status=getattr(inc, "attacker_identity_status", "NOT_CONFIGURED"),
                    attacker_identity_confidence=getattr(inc, "attacker_identity_confidence", "UNKNOWN"),
                    attacker_identity_confidence_score=getattr(inc, "attacker_identity_confidence_score", 0),
                    attacker_identity_observed_at=getattr(inc, "attacker_identity_observed_at", None),
                    attacker_identity_sources=getattr(inc, "attacker_identity_sources", []),
                    attacker_identity_candidates=getattr(inc, "attacker_identity_candidates", []),
                    attacker_identity_diagnostics=getattr(inc, "attacker_identity_diagnostics", []),
                    attacker_attribution=getattr(inc, "attacker_attribution", None),
                    supporting_event_ids=getattr(inc, "supporting_event_ids", []) or [],
                )
                inc.lifecycle_state = new_record.lifecycle_state
                inc.occurrence_count = new_record.occurrence_count
                saved = self.save_incident(new_record)
                records.append(saved)

        return records

    def get_timeline(self, fingerprint: str) -> List[Dict[str, Any]]:
        """Constructs a chronological timeline of an incident across all runs and notes."""
        rec = self.get_incident(fingerprint)
        if not rec:
            return []

        timeline: List[Dict[str, Any]] = []

        # 1. Initial creation entry
        timeline.append({
            "timestamp": rec.first_seen,
            "type": "FIRST_SEEN",
            "title": "Incident Detected",
            "author": "system",
            "description": f"Incident first detected with {rec.event_count} initial event(s). Disposition: {rec.action_taken}.",
            "run_id": rec.run_references[0] if rec.run_references else None,
        })

        # 2. Subsequent run observations
        if len(rec.run_references) > 1:
            for rid in rec.run_references[1:]:
                timeline.append({
                    "timestamp": rec.last_seen,
                    "type": "OBSERVATION",
                    "title": f"Observed in Run {rid}",
                    "author": "system",
                    "description": f"Recurring activity recorded in run {rid}. Severity: {rec.current_severity}.",
                    "run_id": rid,
                })

        # 3. Analyst notes and status transitions
        for note in rec.analyst_notes:
            note_txt = note.get("note", "")
            is_status = "Status changed from" in note_txt or "reopened" in note_txt.lower()
            evt_type = "STATUS_CHANGE" if is_status else "ANALYST_NOTE"
            title = "Status Update" if is_status else "Analyst Note"
            if note_txt.startswith("["):
                closing = note_txt.find("]")
                if closing != -1:
                    custom_type = note_txt[1:closing]
                    evt_type = custom_type
                    title = custom_type.replace("_", " ").title()
                    note_txt = note_txt[closing + 1:].strip()

            timeline.append({
                "timestamp": note.get("timestamp"),
                "type": evt_type,
                "title": title,
                "author": note.get("author", "operator"),
                "description": note_txt,
                "run_id": None,
            })

        # Sort chronologically by timestamp
        timeline.sort(key=lambda item: item.get("timestamp") or "")
        return timeline

    def append_timeline_event(
        self,
        fingerprint: str,
        event_type: str,
        summary: str,
        details: Optional[Dict[str, Any]] = None,
        author: str = "security_agent",
    ) -> bool:
        """Appends a structured event to an incident's notes and timeline."""
        rec = self.get_incident(fingerprint)
        if not rec:
            return False

        note_text = f"[{event_type}] {summary}"
        if details:
            note_text += f" | Details: {json.dumps(details, ensure_ascii=False)}"
        rec.add_note(note=note_text, author=author)
        self.save_incident(rec)
        return True

    def update_incident_attribution(
        self,
        fingerprint: str,
        attribution: Dict[str, Any],
        author: str = "identity_resolver",
    ) -> Optional[IncidentRecord]:
        """Updates attacker identity attribution fields on an incident record and saves it."""
        rec = self.get_incident(fingerprint)
        if not rec:
            return None

        rec.attacker_pc_name = attribution.get("pc_name", "Unknown")
        rec.attacker_fqdn = attribution.get("fqdn", "Unknown")
        rec.attacker_username = attribution.get("username", "Unknown")
        rec.attacker_user_display_name = attribution.get("user_display_name", "Unknown")
        rec.attacker_device_owner = attribution.get("device_owner", "Unknown")
        rec.attacker_mac_address = attribution.get("mac_address", "Unknown")
        rec.attacker_network_scope = attribution.get("network_scope", "UNKNOWN")
        rec.attacker_identity_status = attribution.get("status", "NOT_CONFIGURED")
        rec.attacker_identity_confidence = attribution.get("confidence", "UNKNOWN")
        rec.attacker_identity_confidence_score = attribution.get("confidence_score", 0)
        rec.attacker_identity_observed_at = attribution.get("observed_at")
        rec.attacker_identity_sources = list(attribution.get("sources_queried", []))
        rec.attacker_identity_candidates = list(attribution.get("candidates", []))
        rec.attacker_identity_diagnostics = list(attribution.get("diagnostics", []))
        rec.attacker_attribution = attribution

        status_label = rec.attacker_identity_status
        pc_label = rec.attacker_pc_name if rec.attacker_pc_name not in ("Unknown", "Not applicable") else None
        user_label = rec.attacker_username if rec.attacker_username not in ("Unknown", "Not applicable") else None
        note_parts = [f"Identity resolved to status {status_label} ({rec.attacker_identity_confidence})"]
        if pc_label:
            note_parts.append(f"Computer: {pc_label}")
        if user_label:
            note_parts.append(f"User: {user_label}")
        rec.add_note(" | ".join(note_parts), author=author)

        return self.save_incident(rec)
