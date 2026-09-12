"""
Cross-run incident comparison and historical trend analytics for MNE_Brain Release 2.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.security_review.incidents import IncidentStore
from core.security_review.run_store import SecurityReviewRunStore

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def compare_runs(
    run_id_a: str,
    run_id_b: str,
    run_store: SecurityReviewRunStore,
    incident_store: Optional[IncidentStore] = None,
) -> Dict[str, Any]:
    """Compares two review runs (Run A is earlier/baseline, Run B is later/current).
    Returns categorized differences in detected incidents, severity shifts, and event counts.
    """
    incs_a = run_store.get_incidents(run_id_a) or []
    incs_b = run_store.get_incidents(run_id_b) or []

    run_a_meta = run_store.get_run(run_id_a) or {}
    run_b_meta = run_store.get_run(run_id_b) or {}

    # Map by fingerprint (or incident_id if fingerprint missing)
    map_a = {i.get("fingerprint") or i.get("incident_id"): i for i in incs_a}
    map_b = {i.get("fingerprint") or i.get("incident_id"): i for i in incs_b}

    keys_a = set(map_a.keys())
    keys_b = set(map_b.keys())

    new_keys = keys_b - keys_a
    resolved_keys = keys_a - keys_b
    persisting_keys = keys_a & keys_b

    new_incidents = [map_b[k] for k in new_keys]
    resolved_incidents = [map_a[k] for k in resolved_keys]
    persisting_incidents = [map_b[k] for k in persisting_keys]

    severity_changes: List[Dict[str, Any]] = []
    for k in persisting_keys:
        sev_a = map_a[k].get("severity") or map_a[k].get("current_severity")
        sev_b = map_b[k].get("severity") or map_b[k].get("current_severity")
        if sev_a and sev_b and sev_a != sev_b:
            severity_changes.append({
                "fingerprint": k,
                "title": map_b[k].get("title"),
                "prior_severity": sev_a,
                "current_severity": sev_b,
            })

    total_events_a = sum(i.get("event_count", 1) for i in incs_a)
    total_events_b = sum(i.get("event_count", 1) for i in incs_b)

    summary_parts = []
    if new_incidents:
        summary_parts.append(f"{len(new_incidents)} new incident(s)")
    if resolved_incidents:
        summary_parts.append(f"{len(resolved_incidents)} prior incident(s) no longer observed")
    if persisting_incidents:
        summary_parts.append(f"{len(persisting_incidents)} persisting incident(s)")
    if severity_changes:
        summary_parts.append(f"{len(severity_changes)} incident(s) with severity changes")

    narrative = "; ".join(summary_parts) if summary_parts else "No incident differences observed between runs."

    return {
        "run_id_prior": run_id_a,
        "run_id_current": run_id_b,
        "new_incidents": new_incidents,
        "resolved_incidents": resolved_incidents,
        "persisting_incidents": persisting_incidents,
        "severity_changes": severity_changes,
        "metrics": {
            "incident_count_prior": len(incs_a),
            "incident_count_current": len(incs_b),
            "incident_count_delta": len(incs_b) - len(incs_a),
            "event_count_prior": total_events_a,
            "event_count_current": total_events_b,
            "event_count_delta": total_events_b - total_events_a,
        },
        "summary": narrative,
    }


def get_incident_history(
    fingerprint: str,
    incident_store: IncidentStore,
    run_store: Optional[SecurityReviewRunStore] = None,
) -> Dict[str, Any]:
    """Retrieves full cross-run historical occurrence and trend details for a specific incident."""
    rec = incident_store.get_incident(fingerprint)
    if not rec:
        return {"error": f"Incident '{fingerprint}' not found."}

    timeline = incident_store.get_timeline(fingerprint)
    return {
        "fingerprint": rec.fingerprint,
        "display_id": rec.display_id,
        "title": rec.title,
        "category": rec.category,
        "lifecycle_state": rec.lifecycle_state,
        "current_severity": rec.current_severity,
        "peak_severity": rec.peak_severity,
        "occurrence_count": rec.occurrence_count,
        "first_seen": rec.first_seen,
        "last_seen": rec.last_seen,
        "run_references": rec.run_references,
        "timeline": timeline,
    }


def get_fleet_trends(incident_store: IncidentStore) -> Dict[str, Any]:
    """Aggregates high-level threat trends across the monitored fleet."""
    index = incident_store._load_index()
    records = list(index.values())

    lifecycle_counts = {
        "NEW": 0,
        "RECURRING": 0,
        "INVESTIGATING": 0,
        "RESOLVED": 0,
        "REOPENED": 0,
    }
    severity_counts = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
        "INFO": 0,
    }
    threat_occurrences: Dict[str, int] = {}
    target_occurrences: Dict[str, int] = {}

    for r in records:
        st = r.get("lifecycle_state", "NEW")
        if st in lifecycle_counts:
            lifecycle_counts[st] += 1

        sev = r.get("current_severity", "MEDIUM")
        if sev in severity_counts:
            severity_counts[sev] += 1

        sig = r.get("signature_family") or r.get("title") or "Unknown"
        threat_occurrences[sig] = threat_occurrences.get(sig, 0) + r.get("occurrence_count", 1)

        tgt = r.get("target_identity") or "Perimeter"
        target_occurrences[tgt] = target_occurrences.get(tgt, 0) + 1

    top_threats = sorted(
        [{"threat": k, "occurrences": v} for k, v in threat_occurrences.items()],
        key=lambda x: x["occurrences"],
        reverse=True,
    )[:10]

    top_targets = sorted(
        [{"target": k, "incident_count": v} for k, v in target_occurrences.items()],
        key=lambda x: x["incident_count"],
        reverse=True,
    )[:10]

    return {
        "total_incidents": len(records),
        "lifecycle_counts": lifecycle_counts,
        "severity_counts": severity_counts,
        "top_recurring_threats": top_threats,
        "top_targeted_assets": top_targets,
    }


def categorize_run_incidents_delta(
    run_id: str,
    run_store: SecurityReviewRunStore,
    incident_store: Optional[IncidentStore] = None,
    prior_run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Categorizes incidents in run_id against the immediately prior run:
    - new_incidents: observed for the first time
    - recurring_incidents: repeated from earlier runs
    - increased_severity: severity escalated compared to prior run
    - decreased_severity: severity de-escalated compared to prior run
    - no_longer_observed: observed in prior run but absent in current run
    """
    runs = run_store.list_runs(limit=20)
    current_idx = next((idx for idx, r in enumerate(runs) if r.get("run_id") == run_id), -1)

    current_incidents = run_store.get_incidents(run_id) or []
    prior_incidents: List[Dict[str, Any]] = []

    if prior_run_id:
        prior_incidents = run_store.get_incidents(prior_run_id) or []
    elif current_idx >= 0:
        # Search for prior baseline run, skipping targeted retries that only ran a subset of collectors
        for idx in range(current_idx + 1, len(runs)):
            cand = runs[idx]
            cand_id = cand.get("run_id")
            if cand.get("retry_of_run_id"):
                continue
            prior_run_id = cand_id
            break
        # Fallback to immediate prior if all candidates were retries or none found
        if not prior_run_id and current_idx + 1 < len(runs):
            prior_run_id = runs[current_idx + 1].get("run_id")

        if prior_run_id:
            prior_incidents = run_store.get_incidents(prior_run_id) or []

    curr_map = {i.get("fingerprint") or i.get("incident_id"): i for i in current_incidents}
    prior_map = {i.get("fingerprint") or i.get("incident_id"): i for i in prior_incidents}

    curr_fps = set(curr_map.keys())
    prior_fps = set(prior_map.keys())

    new_fps = curr_fps - prior_fps
    persisting_fps = curr_fps & prior_fps
    no_longer_fps = prior_fps - curr_fps

    new_incidents = [curr_map[fp] for fp in new_fps]
    recurring_incidents = [curr_map[fp] for fp in persisting_fps]
    no_longer_observed = [prior_map[fp] for fp in no_longer_fps]

    increased_severity = []
    decreased_severity = []

    for fp in persisting_fps:
        curr_sev = str(curr_map[fp].get("current_severity") or curr_map[fp].get("severity") or "MEDIUM").upper()
        prior_sev = str(prior_map[fp].get("current_severity") or prior_map[fp].get("severity") or "MEDIUM").upper()
        curr_val = SEVERITY_ORDER.get(curr_sev, 2)
        prior_val = SEVERITY_ORDER.get(prior_sev, 2)
        if curr_val > prior_val:
            increased_severity.append({
                "fingerprint": fp,
                "title": curr_map[fp].get("title"),
                "prior_severity": prior_sev,
                "current_severity": curr_sev,
            })
        elif curr_val < prior_val:
            decreased_severity.append({
                "fingerprint": fp,
                "title": curr_map[fp].get("title"),
                "prior_severity": prior_sev,
                "current_severity": curr_sev,
            })

    return {
        "run_id": run_id,
        "prior_run_id": prior_run_id,
        "new_incidents": new_incidents,
        "recurring_incidents": recurring_incidents,
        "increased_severity": increased_severity,
        "decreased_severity": decreased_severity,
        "no_longer_observed": no_longer_observed,
    }


def get_trend_analytics(
    run_store: SecurityReviewRunStore,
    incident_store: Optional[IncidentStore] = None,
    days: int = 30,
) -> Dict[str, Any]:
    """Computes fleet-wide 7-day and 30-day threat trends, incident lifecycle distribution,
    and per-device/collector query and parsing health trends.
    """
    inc_store = incident_store or getattr(run_store, "incident_store", None)
    runs = run_store.list_runs(limit=100)
    now = datetime.now(timezone.utc)

    # Filter runs within days
    recent_runs = []
    for r in runs:
        c_at = r.get("created_at")
        if c_at:
            try:
                dt = datetime.fromisoformat(str(c_at).replace("Z", "+00:00"))
                if (now - dt).total_seconds() <= days * 86400:
                    recent_runs.append(r)
            except Exception:
                recent_runs.append(r)
        else:
            recent_runs.append(r)

    # 7-day runs
    runs_7d = []
    for r in recent_runs:
        c_at = r.get("created_at")
        if c_at:
            try:
                dt = datetime.fromisoformat(str(c_at).replace("Z", "+00:00"))
                if (now - dt).total_seconds() <= 7 * 86400:
                    runs_7d.append(r)
            except Exception:
                runs_7d.append(r)

    def aggregate_daily(run_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        days_map: Dict[str, Dict[str, Any]] = {}
        for r in run_list:
            d_str = str(r.get("created_at", ""))[:10] or "unknown"
            if d_str not in days_map:
                days_map[d_str] = {
                    "date": d_str,
                    "runs": 0,
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "info": 0,
                    "total": 0,
                }
            counts = r.get("incident_counts", {})
            days_map[d_str]["runs"] += 1
            days_map[d_str]["critical"] += counts.get("CRITICAL", 0)
            days_map[d_str]["high"] += counts.get("HIGH", 0)
            days_map[d_str]["medium"] += counts.get("MEDIUM", 0)
            days_map[d_str]["low"] += counts.get("LOW", 0)
            days_map[d_str]["info"] += counts.get("INFO", 0)
            days_map[d_str]["total"] += sum(counts.values())
        return sorted(days_map.values(), key=lambda x: x["date"])

    daily_7d = aggregate_daily(runs_7d)
    daily_30d = aggregate_daily(recent_runs)

    # Per-collector health trends
    device_health: Dict[str, Dict[str, Any]] = {}
    for r in recent_runs[:20]:
        r_id = r.get("run_id")
        if not r_id:
            continue
        diags = run_store.get_collector_diagnostics(r_id)
        diag_list = diags if isinstance(diags, list) else diags.values() if isinstance(diags, dict) else []
        for d in diag_list:
            if not isinstance(d, dict):
                continue
            dev = d.get("collector") or d.get("device_id") or "unknown"
            if dev not in device_health:
                device_health[dev] = {
                    "collector": dev,
                    "total_runs": 0,
                    "successful_runs": 0,
                    "failed_runs": 0,
                    "total_events": 0,
                    "total_duration_sec": 0.0,
                    "last_status": d.get("status"),
                    "last_error": d.get("error_message"),
                    "last_diagnostic_code": d.get("diagnostic_code"),
                }
            st = d.get("status")
            device_health[dev]["total_runs"] += 1
            if st == "SUCCESS":
                device_health[dev]["successful_runs"] += 1
            else:
                device_health[dev]["failed_runs"] += 1
            device_health[dev]["total_events"] += d.get("events_collected", 0)
            dur = d.get("duration_seconds", 0.0) or (d.get("timing") or {}).get("total_duration_ms", 0) / 1000.0
            device_health[dev]["total_duration_sec"] += float(dur)

    for dev_stat in device_health.values():
        tot = dev_stat["total_runs"]
        dev_stat["success_rate_percent"] = round((dev_stat["successful_runs"] / tot) * 100, 1) if tot else 100.0
        dev_stat["avg_duration_sec"] = round(dev_stat["total_duration_sec"] / tot, 2) if tot else 0.0

    return {
        "period_days": days,
        "runs_analyzed": len(recent_runs),
        "seven_day_trends": daily_7d,
        "thirty_day_trends": daily_30d,
        "device_health_trends": list(device_health.values()),
        "fleet_summary": get_fleet_trends(inc_store) if inc_store else {},
    }
