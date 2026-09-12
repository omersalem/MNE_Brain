"""
Security Analysis Pack Builder for MNE_Brain Release 2.
Constructs bounded, standardized context packs conforming to security-analysis-pack.schema.json
for multi-model AI analysis (Codex and Antigravity).
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.entity.build_entity_index import EntityIndexBuilder
from core.security_review.contracts import validate_contract
from core.security_review.run_store import SecurityReviewRunStore

logger = logging.getLogger(__name__)

MAX_RUN_PACK_CHARS = 18000
MAX_INCIDENT_PACK_CHARS = 12000

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


def _compact_incident_dict(inc: Dict[str, Any], max_desc_len: int = 150) -> Dict[str, Any]:
    attr = inc.get("attacker_attribution")
    compact_attr = None
    if isinstance(attr, dict):
        compact_attr = {
            "status": attr.get("status"),
            "pc_name": attr.get("pc_name"),
            "username": attr.get("username"),
            "confidence": attr.get("confidence"),
            "confidence_score": attr.get("confidence_score"),
        }
    desc = str(inc.get("description") or "")
    if len(desc) > max_desc_len:
        desc = desc[: max_desc_len - 3] + "..."
    return {
        "fingerprint": inc.get("fingerprint") or inc.get("incident_id"),
        "display_id": inc.get("display_id"),
        "title": inc.get("title"),
        "severity": inc.get("severity") or inc.get("current_severity", "UNKNOWN"),
        "category": inc.get("category"),
        "source_device": inc.get("source_device"),
        "attacker_ip": inc.get("attacker_ip") or inc.get("attacker_identity"),
        "target": inc.get("target") or inc.get("target_identity"),
        "action_taken": inc.get("action_taken"),
        "event_count": inc.get("event_count", 1),
        "description": desc,
        "attacker_attribution": compact_attr,
        "remediation_cli": inc.get("remediation_cli"),
    }


def _compact_event_dict(ev: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "event_id": ev.get("event_id"),
        "timestamp": str(ev.get("timestamp")),
        "source_device": ev.get("source_device"),
        "threat_name": ev.get("threat_name"),
        "attacker_ip": ev.get("attacker_ip"),
        "target": ev.get("target"),
        "action_taken": ev.get("action_taken"),
    }


class SecurityAnalysisPackBuilder:
    """Builds bounded, schema-compliant context packs for AI security analysis."""

    def __init__(
        self,
        run_store: Optional[SecurityReviewRunStore] = None,
        entity_index: Optional[EntityIndexBuilder] = None,
        base_dir: Optional[Path] = None,
    ):
        self.run_store = run_store or SecurityReviewRunStore()
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.entity_index = entity_index or EntityIndexBuilder(self.base_dir)

    def _generate_pack_id(self) -> str:
        timestamp = int(time.time())
        unique = uuid.uuid4().hex[:6]
        return f"pack-{timestamp}-{unique}"

    def _find_canonical_entities(self, names_or_ips: List[str]) -> List[Dict[str, Any]]:
        """Resolves target names or IPs against documented knowledge layer."""
        entities: List[Dict[str, Any]] = []
        seen_ids = set()
        for term in names_or_ips:
            if not term or str(term).lower() in ("unknown", "none", "n/a", ""):
                continue
            try:
                matches = self.entity_index.resolve_entity(str(term))
                for ent in matches:
                    eid = ent.get("entity_id")
                    if eid and eid not in seen_ids:
                        seen_ids.add(eid)
                        entities.append({
                            "entity_id": eid,
                            "name": ent.get("name", eid),
                            "hostname": ent.get("hostname"),
                            "ip": ent.get("ip"),
                            "role": ent.get("role", ent.get("device_type", "unknown")),
                            "source_file": ent.get("canonical_file", ""),
                        })
            except Exception as exc:
                logger.debug("Entity lookup failed for %s: %s", term, exc)
        return entities

    def _find_runbooks(self, categories_or_keywords: List[str]) -> List[Dict[str, Any]]:
        """Discovers matching SOP runbooks from intelligence/runbooks."""
        matching: List[Dict[str, Any]] = []
        runbooks_dir = self.base_dir / "intelligence" / "runbooks"
        if not runbooks_dir.exists():
            return matching

        keywords = [k.lower() for k in categories_or_keywords if k]
        seen_files = set()

        for md_path in sorted(runbooks_dir.glob("*.md")):
            name = md_path.stem.lower()
            matches = any(kw in name for kw in keywords) or "triage" in name
            if matches and md_path.name not in seen_files:
                seen_files.add(md_path.name)
                try:
                    title = md_path.stem.replace("-", " ").title()
                    matching.append({
                        "runbook_id": md_path.stem,
                        "title": title,
                        "relative_path": f"intelligence/runbooks/{md_path.name}",
                        "category": "incident-triage",
                    })
                except Exception:
                    pass
            if len(matching) >= 3:
                break
        return matching

    def build_run_pack(
        self,
        run_id: str,
        max_chars: int = MAX_RUN_PACK_CHARS,
    ) -> Dict[str, Any]:
        """Constructs an analysis pack for an entire security review run."""
        run_data = self.run_store.get_run(run_id)
        if not run_data:
            raise ValueError(f"Run '{run_id}' not found.")

        events = self.run_store.get_events(run_id)
        incidents = self.run_store.get_incidents(run_id)
        diagnostics_raw = self.run_store.get_collector_diagnostics(run_id)

        collector_diagnostics: List[Dict[str, Any]] = []
        if isinstance(diagnostics_raw, dict):
            collector_diagnostics = list(diagnostics_raw.values())
        elif isinstance(diagnostics_raw, list):
            collector_diagnostics = diagnostics_raw

        run_summary = {
            "run_id": run_data.get("run_id", run_id),
            "created_at": run_data.get("created_at"),
            "completed_at": run_data.get("completed_at"),
            "state": run_data.get("state"),
            "stage": run_data.get("stage"),
            "incident_counts": run_data.get("incident_counts", {}),
            "total_events": len(events),
            "warnings": run_data.get("warnings", []),
        }

        target_names: List[str] = []
        for inc in incidents:
            if inc.get("target"):
                target_names.append(inc["target"])
            if inc.get("attacker_ip"):
                target_names.append(inc["attacker_ip"])
            for dev in inc.get("devices_involved", []):
                target_names.append(dev)
        canonical_entities = self._find_canonical_entities(list(set(target_names)))

        categories = list({str(inc.get("category", "")) for inc in incidents})
        runbooks = self._find_runbooks(categories)

        sources: List[str] = [
            f"operations/security_review/runs/{run_id}/run.json",
            f"operations/security_review/runs/{run_id}/incidents.json",
            f"operations/security_review/runs/{run_id}/collector_diagnostics.json",
        ]
        for ent in canonical_entities:
            if ent.get("source_file"):
                sources.append(ent["source_file"])
        for rb in runbooks:
            sources.append(rb["relative_path"])

        unknowns = [
            "Historical telemetry beyond the requested query window was not evaluated.",
            "Live network session state and firewall connection tables were not inspected.",
            "External threat intelligence lookups were not performed.",
        ]

        # Prioritize incidents by severity: CRITICAL > HIGH > MEDIUM > LOW > INFO
        sorted_incidents = sorted(
            incidents,
            key=lambda x: SEVERITY_ORDER.get(str(x.get("severity") or x.get("current_severity") or "").upper(), 9),
        )
        compact_incidents = [_compact_incident_dict(inc) for inc in sorted_incidents]
        compact_events = [_compact_event_dict(ev) for ev in events[:10]]

        pack: Dict[str, Any] = {
            "pack_id": self._generate_pack_id(),
            "target_type": "RUN",
            "run_id": run_id,
            "incident_fingerprints": [i["fingerprint"] for i in compact_incidents if i.get("fingerprint")],
            "run_summary": run_summary,
            "incidents": compact_incidents,
            "supporting_events": compact_events,
            "collector_diagnostics": collector_diagnostics,
            "matching_canonical_entities": canonical_entities,
            "related_adjacencies": [],
            "matching_runbooks": runbooks,
            "earlier_occurrences_trend": {},
            "unknowns": unknowns,
            "sources": sorted(set(sources)),
        }

        return self._compact_pack(pack, max_chars)

    def build_incident_pack(
        self,
        fingerprint: str,
        run_id: Optional[str] = None,
        max_chars: int = MAX_INCIDENT_PACK_CHARS,
    ) -> Dict[str, Any]:
        """Constructs an analysis pack focused on a single security incident."""
        incident_rec = self.run_store.get_incident_record(fingerprint)
        if not incident_rec:
            raise ValueError(f"Incident with fingerprint '{fingerprint}' not found.")

        inc_dict = incident_rec.to_dict()
        actual_run_id = run_id or (incident_rec.run_references[-1] if incident_rec.run_references else None)

        events: List[Dict[str, Any]] = []
        collector_diagnostics: List[Dict[str, Any]] = []
        run_summary: Dict[str, Any] = {}

        if actual_run_id:
            run_data = self.run_store.get_run(actual_run_id)
            if run_data:
                run_summary = {
                    "run_id": actual_run_id,
                    "created_at": run_data.get("created_at"),
                    "completed_at": run_data.get("completed_at"),
                    "state": run_data.get("state"),
                    "stage": run_data.get("stage"),
                    "incident_counts": run_data.get("incident_counts", {}),
                }
            all_events = self.run_store.get_events(actual_run_id)
            supporting_ids = set(getattr(incident_rec, "supporting_event_ids", []) or [])
            events = [e for e in all_events if e.get("event_id") in supporting_ids or e.get("threat_name") == incident_rec.title]
            if not events:
                events = all_events[:5]

            diags_raw = self.run_store.get_collector_diagnostics(actual_run_id)
            if isinstance(diags_raw, dict):
                collector_diagnostics = list(diags_raw.values())
            elif isinstance(diags_raw, list):
                collector_diagnostics = diags_raw
        else:
            run_summary = {
                "run_id": "NONE",
                "created_at": incident_rec.first_seen,
                "state": "STANDALONE",
                "incident_counts": {"total": 1},
            }

        attacker = getattr(incident_rec, "attacker_identity", "") or getattr(incident_rec, "attacker_ip", "")
        target = getattr(incident_rec, "target_identity", "") or getattr(incident_rec, "target", "")
        lookup_terms = [target, attacker, incident_rec.source_device]
        if getattr(incident_rec, "attacker_pc_name", None):
            lookup_terms.append(incident_rec.attacker_pc_name)
        canonical_entities = self._find_canonical_entities(list(set(lookup_terms)))

        runbooks = self._find_runbooks([incident_rec.category, incident_rec.signature_family])

        trend_info = {
            "first_seen": incident_rec.first_seen,
            "last_seen": incident_rec.last_seen,
            "occurrence_count": incident_rec.occurrence_count,
            "lifecycle_state": incident_rec.lifecycle_state,
            "associated_runs_count": len(incident_rec.run_references),
        }

        sources = [
            f"operations/security_review/incidents/{fingerprint}.json",
        ]
        if actual_run_id and actual_run_id != "NONE":
            sources.append(f"operations/security_review/runs/{actual_run_id}/run.json")
        for ent in canonical_entities:
            if ent.get("source_file"):
                sources.append(ent["source_file"])
        for rb in runbooks:
            sources.append(rb["relative_path"])

        unknowns = [
            f"Whether attacker identity '{attacker}' represents a shared NAT or spoofed origin.",
            f"Active port state on target '{target}' was not verified live.",
            "Whether similar alerts were dropped upstream before collector observation.",
        ]

        scope = getattr(incident_rec, "attacker_network_scope", None)
        id_status = getattr(incident_rec, "attacker_identity_status", None)
        pc_name = getattr(incident_rec, "attacker_pc_name", None)
        user = getattr(incident_rec, "attacker_username", None)
        owner = getattr(incident_rec, "attacker_device_owner", None)

        if scope == "LOCAL":
            if id_status == "RESOLVED":
                unknowns.append(f"Attacker device {pc_name} confirmed; user {user} active at incident time.")
            elif id_status == "PARTIAL":
                unknowns.append(f"Attacker device identified as {pc_name or owner or 'partial'}; domain user session was unconfirmed or absent.")
            elif id_status == "AMBIGUOUS":
                unknowns.append(f"Attacker identity for {attacker} is AMBIGUOUS due to conflicting records across directory/network sources.")
            elif id_status == "NOT_FOUND":
                unknowns.append(f"Attacker IP {attacker} is in local subnet but returned no match across DHCP, SCCM, AD, or VPN.")

        pack: Dict[str, Any] = {
            "pack_id": self._generate_pack_id(),
            "target_type": "INCIDENT",
            "run_id": actual_run_id or "NONE",
            "incident_fingerprints": [fingerprint],
            "run_summary": run_summary,
            "incidents": [_compact_incident_dict(inc_dict)],
            "supporting_events": [_compact_event_dict(e) for e in events[:10]],
            "collector_diagnostics": collector_diagnostics,
            "matching_canonical_entities": canonical_entities,
            "related_adjacencies": [],
            "matching_runbooks": runbooks,
            "earlier_occurrences_trend": trend_info,
            "unknowns": unknowns,
            "sources": sorted(set(sources)),
        }

        return self._compact_pack(pack, max_chars)

    def build_incidents_pack(
        self,
        fingerprints: List[str],
        run_id: Optional[str] = None,
        max_chars: int = MAX_RUN_PACK_CHARS,
    ) -> Dict[str, Any]:
        """Constructs an analysis pack for a selected subset of incidents."""
        incidents: List[Dict[str, Any]] = []
        for fp in fingerprints:
            rec = self.run_store.get_incident_record(fp)
            if rec:
                incidents.append(rec.to_dict())

        if not incidents:
            raise ValueError("No valid incidents found for provided fingerprints.")

        run_summary: Dict[str, Any] = {}
        collector_diagnostics: List[Dict[str, Any]] = []
        events: List[Dict[str, Any]] = []

        if run_id:
            run_data = self.run_store.get_run(run_id)
            if run_data:
                run_summary = {
                    "run_id": run_id,
                    "created_at": run_data.get("created_at"),
                    "state": run_data.get("state"),
                    "incident_counts": run_data.get("incident_counts", {}),
                }
            all_events = self.run_store.get_events(run_id)
            events = all_events[:15]
            diags_raw = self.run_store.get_collector_diagnostics(run_id)
            if isinstance(diags_raw, dict):
                collector_diagnostics = list(diags_raw.values())
            elif isinstance(diags_raw, list):
                collector_diagnostics = diags_raw
        else:
            run_summary = {
                "run_id": "SELECTION",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "state": "COMPLETED",
                "incident_counts": {"total": len(incidents)},
            }

        target_names: List[str] = []
        categories: List[str] = []
        for inc in incidents:
            if inc.get("target"):
                target_names.append(inc["target"])
            if inc.get("attacker_ip"):
                target_names.append(inc["attacker_ip"])
            if inc.get("category"):
                categories.append(inc["category"])

        canonical_entities = self._find_canonical_entities(list(set(target_names)))
        runbooks = self._find_runbooks(list(set(categories)))

        sources = [f"operations/security_review/incidents/{fp}.json" for fp in fingerprints]
        if run_id:
            sources.append(f"operations/security_review/runs/{run_id}/run.json")
        for ent in canonical_entities:
            if ent.get("source_file"):
                sources.append(ent["source_file"])

        unknowns = [
            "Cross-device correlation is limited to observed log records.",
            "Internal east-west lateral movement was not fully mapped.",
        ]

        sorted_incidents = sorted(
            incidents,
            key=lambda x: SEVERITY_ORDER.get(str(x.get("severity") or x.get("current_severity") or "").upper(), 9),
        )
        compact_incidents = [_compact_incident_dict(inc) for inc in sorted_incidents]

        pack: Dict[str, Any] = {
            "pack_id": self._generate_pack_id(),
            "target_type": "INCIDENTS",
            "run_id": run_id or "SELECTION",
            "incident_fingerprints": [i["fingerprint"] for i in compact_incidents if i.get("fingerprint")],
            "run_summary": run_summary,
            "incidents": compact_incidents,
            "supporting_events": [_compact_event_dict(e) for e in events[:15]],
            "collector_diagnostics": collector_diagnostics,
            "matching_canonical_entities": canonical_entities,
            "related_adjacencies": [],
            "matching_runbooks": runbooks,
            "earlier_occurrences_trend": {},
            "unknowns": unknowns,
            "sources": sorted(set(sources)),
        }

        return self._compact_pack(pack, max_chars)

    def _compact_pack(self, pack: Dict[str, Any], max_chars: int) -> Dict[str, Any]:
        """Progressively trims non-essential fields to guarantee serialized size <= max_chars."""
        pack["character_count"] = 0

        # Step 1: progressive incident count capping if over max_chars
        serialized = json.dumps(pack, ensure_ascii=False)
        if len(serialized) > max_chars and pack.get("incidents"):
            incs = pack["incidents"]
            for cap in (25, 20, 15, 10, 7, 5, 3, 2, 1):
                if len(serialized) <= max_chars:
                    break
                pack["incidents"] = incs[:cap]
                pack["incident_fingerprints"] = [
                    i.get("fingerprint") or i.get("incident_id")
                    for i in pack["incidents"]
                    if i.get("fingerprint") or i.get("incident_id")
                ]
                serialized = json.dumps(pack, ensure_ascii=False)

        # Step 2: trim supporting events
        if len(serialized) > max_chars and pack.get("supporting_events"):
            pack["supporting_events"] = pack["supporting_events"][:3]
            serialized = json.dumps(pack, ensure_ascii=False)

        if len(serialized) > max_chars and pack.get("supporting_events"):
            pack["supporting_events"] = []
            serialized = json.dumps(pack, ensure_ascii=False)

        # Step 3: compact collector diagnostics
        if len(serialized) > max_chars and pack.get("collector_diagnostics"):
            compact_diags = []
            for d in pack["collector_diagnostics"]:
                if isinstance(d, dict):
                    compact_diags.append({
                        "device_name": d.get("device_name", ""),
                        "status": d.get("status", "UNKNOWN"),
                        "records_fetched": d.get("records_fetched", 0),
                    })
            pack["collector_diagnostics"] = compact_diags
            serialized = json.dumps(pack, ensure_ascii=False)

        # Step 4: trim descriptions further if still over budget
        if len(serialized) > max_chars and pack.get("incidents"):
            for inc in pack["incidents"]:
                desc = str(inc.get("description") or "")
                if len(desc) > 80:
                    inc["description"] = desc[:77] + "..."
            serialized = json.dumps(pack, ensure_ascii=False)

        # Step 5: trim canonical entities, runbooks, and sources if still over budget
        if len(serialized) > max_chars:
            pack["matching_canonical_entities"] = pack.get("matching_canonical_entities", [])[:2]
            pack["matching_runbooks"] = pack.get("matching_runbooks", [])[:2]
            pack["sources"] = pack.get("sources", [])[:5]
            serialized = json.dumps(pack, ensure_ascii=False)

        # Step 6: emergency reduction to top 1 minimal incident
        if len(serialized) > max_chars and len(pack.get("incidents", [])) > 1:
            pack["incidents"] = pack["incidents"][:1]
            pack["incident_fingerprints"] = [
                i.get("fingerprint") or i.get("incident_id")
                for i in pack["incidents"]
                if i.get("fingerprint") or i.get("incident_id")
            ]
            serialized = json.dumps(pack, ensure_ascii=False)

        pack["character_count"] = len(serialized)
        final_serialized = json.dumps(pack, ensure_ascii=False)
        pack["character_count"] = len(final_serialized)

        try:
            validate_contract(pack, "security-analysis-pack.schema.json")
        except Exception as exc:
            logger.warning("Analysis pack schema validation warning: %s", exc)

        return pack
