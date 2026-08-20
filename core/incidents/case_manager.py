#!/usr/bin/env python3
"""Offline incident impact, ownership, continuation, and handoff management."""

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from core.orchestration.incident_orchestrator import IncidentOrchestrator
from core.runbooks.registry import RunbookRegistry


class IncidentCaseManager:
    """Wrap a P3 investigation in an offline, non-notifying case packet."""

    MODE = "OFFLINE_CASE_MANAGEMENT"
    _SCOPES = {
        "unknown",
        "single_user",
        "multiple_users",
        "branch",
        "multiple_branches",
        "ministry_wide",
    }
    _AVAILABILITY = {"unknown", "unavailable", "degraded", "intermittent"}
    _UPDATE_STATUSES = {"COLLECTED_REPORTED", "FAILED_REPORTED", "SKIPPED_REPORTED"}
    _REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
    _SERVICE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._:/()&+-]{1,127}$")

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.policy_path = self.base_dir / "config" / "p4_incident_policy.yaml"
        self.schema_path = self.base_dir / "00_meta" / "schemas" / "incident-case.schema.json"
        self.policy = self._load_mapping(self.policy_path)
        self.schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        self.limits = self.policy.get("limits", {})
        self.orchestrator = IncidentOrchestrator(base_dir=self.base_dir)
        self.runbook_registry = RunbookRegistry(base_dir=self.base_dir)

    @staticmethod
    def _load_mapping(path: Path) -> dict[str, Any]:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"{path.name} must contain a mapping")
        return payload

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _parse_timestamp(value: Any, field_name: str) -> str | None:
        if value in (None, ""):
            return None
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be an ISO-8601 string or null")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an ISO-8601 timestamp") from exc
        if parsed.tzinfo is None:
            raise ValueError(f"{field_name} must include a timezone")
        if parsed.astimezone(timezone.utc) > datetime.now(timezone.utc):
            raise ValueError(f"{field_name} cannot be in the future")
        return parsed.astimezone(timezone.utc).isoformat()

    def _normalise_impact(self, impact_context: Any) -> dict[str, Any]:
        if impact_context in (None, {}):
            return {
                "status": "NOT_PROVIDED",
                "source": "operator_report",
                "affected_service": None,
                "affected_scope": "unknown",
                "availability": "unknown",
                "branch_references": [],
                "affected_user_count": None,
                "security_impact_reported": False,
                "data_loss_suspected": False,
                "public_service_reported": False,
                "owner_reference": None,
                "reporter_reference": None,
                "reported_at": None,
            }
        if not isinstance(impact_context, dict):
            raise ValueError("impact_context must be a mapping")
        allowed = {
            "affected_service",
            "affected_scope",
            "availability",
            "branch_references",
            "affected_user_count",
            "security_impact_reported",
            "data_loss_suspected",
            "public_service_reported",
            "owner_reference",
            "reporter_reference",
            "reported_at",
        }
        extra = set(impact_context) - allowed
        if extra:
            raise ValueError(f"impact_context contains unsupported fields: {', '.join(sorted(extra))}")
        scope = impact_context.get("affected_scope", "unknown")
        availability = impact_context.get("availability", "unknown")
        if scope not in self._SCOPES:
            raise ValueError("affected_scope is not in the P4 allowlist")
        if availability not in self._AVAILABILITY:
            raise ValueError("availability is not in the P4 allowlist")
        boolean_fields = (
            "security_impact_reported",
            "data_loss_suspected",
            "public_service_reported",
        )
        for field in boolean_fields:
            if field in impact_context and not isinstance(impact_context[field], bool):
                raise ValueError(f"{field} must be boolean")
        reporter_reference = impact_context.get("reporter_reference")
        if reporter_reference is not None and (
            not isinstance(reporter_reference, str)
            or not self._REFERENCE.fullmatch(reporter_reference)
        ):
            raise ValueError("reporter_reference must be an opaque reference, not free text")
        owner_reference = impact_context.get("owner_reference")
        if owner_reference is not None and (
            not isinstance(owner_reference, str)
            or owner_reference != "MNE-BRAIN-OWNER"
        ):
            raise ValueError("owner_reference must be MNE-BRAIN-OWNER")
        affected_service = impact_context.get("affected_service")
        if affected_service is not None and (
            not isinstance(affected_service, str)
            or not self._SERVICE.fullmatch(affected_service)
        ):
            raise ValueError("affected_service has an invalid format")
        branches = impact_context.get("branch_references", [])
        if (
            not isinstance(branches, list)
            or len(branches) > 10
            or len(set(branches)) != len(branches)
            or any(
            not isinstance(item, str) or not self._REFERENCE.fullmatch(item) for item in branches
            )
        ):
            raise ValueError("branch_references must contain at most ten opaque references")
        user_count = impact_context.get("affected_user_count")
        if user_count is not None and (
            isinstance(user_count, bool)
            or not isinstance(user_count, int)
            or not 0 <= user_count <= 1000000
        ):
            raise ValueError("affected_user_count must be an integer from 0 to 1000000")
        return {
            "status": "REPORTED_NOT_VERIFIED",
            "source": "operator_report",
            "affected_service": affected_service,
            "affected_scope": scope,
            "availability": availability,
            "branch_references": branches,
            "affected_user_count": user_count,
            "security_impact_reported": bool(impact_context.get("security_impact_reported", False)),
            "data_loss_suspected": bool(impact_context.get("data_loss_suspected", False)),
            "public_service_reported": bool(impact_context.get("public_service_reported", False)),
            "owner_reference": owner_reference,
            "reporter_reference": reporter_reference,
            "reported_at": self._parse_timestamp(impact_context.get("reported_at"), "reported_at"),
        }

    @staticmethod
    def _priority(impact: dict[str, Any]) -> dict[str, Any]:
        scope = impact["affected_scope"]
        availability = impact["availability"]
        reasons: list[str] = []
        if impact["status"] == "NOT_PROVIDED":
            classification = "UNASSESSED"
            reasons.append("Impact scope and availability were not provided.")
        elif impact["security_impact_reported"] or impact["data_loss_suspected"]:
            classification = "PROVISIONAL_P1"
            reasons.append("Operator reported security impact or suspected data loss.")
        elif scope == "unknown" and availability == "unknown":
            classification = "UNASSESSED"
            reasons.append("Impact scope and availability were not provided.")
        elif scope == "ministry_wide" and availability in {"unavailable", "degraded", "intermittent"}:
            classification = "PROVISIONAL_P1"
            reasons.append(f"Operator reported {availability} ministry-wide impact.")
        elif scope == "multiple_branches" and availability == "unavailable":
            classification = "PROVISIONAL_P1"
            reasons.append("Operator reported an unavailable service across multiple branches.")
        elif (
            (scope == "branch" and availability == "unavailable")
            or (scope == "multiple_users" and availability == "unavailable")
            or (scope == "multiple_branches" and availability in {"degraded", "intermittent"})
            or (impact["public_service_reported"] and availability == "unavailable")
        ):
            classification = "PROVISIONAL_P2"
            reasons.append("Reported impact meets the configured offline P2 triage rule.")
        elif (
            (scope == "multiple_users" and availability in {"degraded", "intermittent"})
            or (scope == "single_user" and availability == "unavailable")
            or (scope == "branch" and availability in {"degraded", "intermittent"})
        ):
            classification = "PROVISIONAL_P3"
            reasons.append("Reported impact meets the configured offline P3 triage rule.")
        else:
            classification = "PROVISIONAL_P4"
            reasons.append("Reported impact meets only the configured offline P4 triage rule.")
        return {
            "classification": classification,
            "basis": "REPORTED_IMPACT_ONLY",
            "owner_confirmation_required": True,
            "reasons": reasons,
        }

    def _ownership(self, investigation: dict[str, Any]) -> dict[str, Any]:
        target = investigation.get("target")
        return {
            "primary": {
                "team": "MNE-BRAIN-OWNER" if target else "UNASSIGNED",
                "basis": "SOLE_OWNER_POLICY" if target else "TARGET_REQUIRED",
                "notification_sent": False,
            },
            "supporting": [],
            "routing_status": "OWNER_CONTROLLED_NOT_NOTIFIED",
        }

    def _normalise_updates(
        self,
        check_updates: Any,
        allowed_check_ids: set[str],
        now: str,
    ) -> list[dict[str, Any]]:
        if check_updates in (None, []):
            return []
        if not isinstance(check_updates, list):
            raise ValueError("check_updates must be a list")
        limit = int(self.limits.get("max_check_updates", 5))
        if len(check_updates) > limit:
            raise ValueError("check_updates exceed the configured budget")
        normalised: list[dict[str, Any]] = []
        seen: set[str] = set()
        for update in check_updates:
            if not isinstance(update, dict) or set(update) - {"check_id", "status", "note", "reference_ids"}:
                raise ValueError("each check update must use only check_id, status, note, and reference_ids")
            check_id = update.get("check_id")
            status = update.get("status")
            note = update.get("note")
            reference_ids = update.get("reference_ids", [])
            if check_id not in allowed_check_ids or check_id in seen:
                raise ValueError("check update is duplicate or outside the case objective allowlist")
            if status not in self._UPDATE_STATUSES:
                raise ValueError("check update status is not allowed")
            if note is not None and (not isinstance(note, str) or len(note) > int(self.limits.get("max_note_chars", 300))):
                raise ValueError("check update note is invalid or too long")
            if not isinstance(reference_ids, list) or len(reference_ids) > 3 or any(
                not isinstance(item, str) or not self._REFERENCE.fullmatch(item) for item in reference_ids
            ):
                raise ValueError("reference_ids must contain at most three opaque references")
            normalised.append(
                {
                    "check_id": check_id,
                    "status": status,
                    "source": "operator_report",
                    "verified_evidence": False,
                    "note": note,
                    "reference_ids": reference_ids,
                    "updated_at": now,
                }
            )
            seen.add(check_id)
        return normalised

    @staticmethod
    def _case_state(
        investigation: dict[str, Any], priority: dict[str, Any], pending_checks: list[dict[str, Any]]
    ) -> str:
        if investigation.get("target") is None:
            return "NEEDS_TARGET"
        if priority["classification"] == "UNASSESSED":
            return "IMPACT_REQUIRED"
        if investigation["status"] == "CONFLICTING_EVIDENCE":
            return "CONFLICTING_EVIDENCE"
        if investigation["status"] == "EVIDENCE_SUPPORTED":
            return "EVIDENCE_REVIEW"
        return "AWAITING_EVIDENCE" if pending_checks else "HANDOFF_READY"

    def _handoff(
        self,
        case_id: str,
        case_state: str,
        priority: dict[str, Any],
        impact: dict[str, Any],
        investigation: dict[str, Any],
        ownership: dict[str, Any],
        runbook_guidance: dict[str, Any],
        history: list[dict[str, Any]],
        pending_checks: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
    ) -> dict[str, Any]:
        blockers = list(investigation.get("evidence_pack", {}).get("unknowns", []))
        if priority["classification"] == "UNASSESSED":
            blockers.append("Impact scope and availability require operator input.")
        if investigation.get("reasoning", {}).get("accepted_evidence_refs"):
            blockers.append("Accepted live evidence remains scoped to its checks and freshness window.")
        else:
            blockers.append("Fresh attributable evidence is still required for an operational conclusion.")
        packet = {
            "case_id": case_id,
            "case_state": case_state,
            "priority": priority,
            "impact": impact,
            "target": investigation.get("target"),
            "ownership": ownership,
            "runbook_guidance": json.loads(json.dumps(runbook_guidance)),
            "reasoning_status": investigation.get("reasoning", {}).get("reasoning_status"),
            "accepted_evidence_refs": investigation.get("reasoning", {}).get("accepted_evidence_refs", []),
            "unknowns_and_blockers": blockers,
            "reported_check_history": history,
            "pending_evidence_objectives": pending_checks,
            "timeline": timeline[-8:],
            "response_target": "NO_CONFIGURED_RESPONSE_TARGET",
            "instruction": (
                "The sole owner confirms priority and scope. Treat impact and check outcomes as "
                "reported, not verified. Do not notify teams or execute an objective from this packet."
            ),
        }
        max_chars = int(self.limits.get("max_handoff_chars", 8000))
        while len(json.dumps(packet, sort_keys=True)) > max_chars and packet["timeline"]:
            packet["timeline"].pop(0)
        while len(json.dumps(packet, sort_keys=True)) > max_chars and packet["reported_check_history"]:
            packet["reported_check_history"].pop(0)
        while len(json.dumps(packet, sort_keys=True)) > max_chars and packet["pending_evidence_objectives"]:
            packet["pending_evidence_objectives"].pop()
        while (
            len(json.dumps(packet, sort_keys=True)) > max_chars
            and packet["runbook_guidance"].get("candidates")
        ):
            packet["runbook_guidance"]["candidates"].pop()
            packet["runbook_guidance"]["candidate_count"] = len(
                packet["runbook_guidance"]["candidates"]
            )
        if len(json.dumps(packet, sort_keys=True)) > max_chars:
            packet["unknowns_and_blockers"] = ["Additional blockers omitted to preserve handoff budget."]
        return packet

    def build_case(
        self,
        question: str,
        *,
        impact_context: dict[str, Any] | None = None,
        prior_case: dict[str, Any] | None = None,
        check_updates: list[dict[str, Any]] | None = None,
        verification_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        investigation = self.orchestrator.investigate(
            question,
            verification_result=verification_result,
        )
        now = self._now()
        impact_was_provided = impact_context not in (None, {})
        impact = self._normalise_impact(impact_context)
        priority = self._priority(impact)

        if prior_case is not None:
            try:
                jsonschema.validate(
                    instance=prior_case,
                    schema=self.schema,
                    format_checker=jsonschema.FormatChecker(),
                )
            except jsonschema.ValidationError as exc:
                raise ValueError("prior_case is not a valid P4 case") from exc
            prior_target = (prior_case.get("target") or {}).get("entity_id")
            current_target = (investigation.get("target") or {}).get("entity_id")
            if prior_case.get("question") != question.strip() or prior_target != current_target:
                raise ValueError("prior_case question or target does not match this continuation")
            if not impact_was_provided:
                impact = dict(prior_case["impact"])
                priority = self._priority(impact)
            case_id = prior_case["case_id"]
            opened_at = prior_case["opened_at"]
            existing_history = list(prior_case.get("check_history", []))
            timeline = list(prior_case.get("timeline", []))
            event_type = "CASE_CONTINUED"
        else:
            digest = hashlib.sha256(investigation["investigation_id"].encode("utf-8")).hexdigest()[:12]
            case_id = f"case-p4-{digest}"
            opened_at = now
            existing_history = []
            timeline = []
            event_type = "CASE_OPENED"

        candidate_checks = investigation.get("next_checks", [])
        allowed_check_ids = {item["check_id"] for item in candidate_checks}
        allowed_check_ids.update(item.get("check_id") for item in existing_history)
        updates = self._normalise_updates(check_updates, allowed_check_ids, now)
        history_by_id = {
            item["check_id"]: item for item in existing_history if item.get("check_id")
        }
        for update in updates:
            history_by_id[update["check_id"]] = update
        history = [history_by_id[key] for key in sorted(history_by_id)][: int(self.limits.get("max_check_updates", 5))]

        suppressed = {
            item["check_id"]
            for item in history
            if item["status"] in {"COLLECTED_REPORTED", "SKIPPED_REPORTED"}
        }
        failed = {item["check_id"] for item in history if item["status"] == "FAILED_REPORTED"}
        pending_checks = []
        for item in candidate_checks:
            if item["check_id"] in suppressed:
                continue
            candidate = dict(item)
            candidate["requires_review_before_retry"] = item["check_id"] in failed
            pending_checks.append(candidate)

        ownership = self._ownership(investigation)
        runbook_guidance = self.runbook_registry.select_for_target(investigation.get("target"))
        case_state = self._case_state(investigation, priority, pending_checks)
        timeline.append(
            {
                "event_type": event_type,
                "occurred_at": now,
                "source": "p4_case_manager",
                "truth_status": "SYSTEM_RECORDED",
            }
        )
        if impact["status"] == "REPORTED_NOT_VERIFIED" and impact_was_provided:
            timeline.append(
                {
                    "event_type": "IMPACT_REPORTED",
                    "occurred_at": impact["reported_at"] or now,
                    "source": "operator_report",
                    "truth_status": "REPORTED_NOT_VERIFIED",
                }
            )
        for update in updates:
            timeline.append(
                {
                    "event_type": "CHECK_OUTCOME_REPORTED",
                    "check_id": update["check_id"],
                    "occurred_at": update["updated_at"],
                    "source": "operator_report",
                    "truth_status": "REPORTED_NOT_VERIFIED",
                }
            )
        timeline = timeline[-int(self.limits.get("max_timeline_events", 20)) :]

        handoff = self._handoff(
            case_id,
            case_state,
            priority,
            impact,
            investigation,
            ownership,
            runbook_guidance,
            history,
            pending_checks,
            timeline,
        )
        owner_routes = 1 + len(ownership["supporting"]) if investigation.get("target") else 0
        result = {
            "case_id": case_id,
            "mode": self.MODE,
            "case_state": case_state,
            "opened_at": opened_at,
            "updated_at": now,
            "question": question.strip(),
            "priority": priority,
            "impact": impact,
            "target": investigation.get("target"),
            "ownership": ownership,
            "runbook_guidance": runbook_guidance,
            "investigation": investigation,
            "check_history": history,
            "pending_checks": pending_checks,
            "timeline": timeline,
            "handoff_packet": handoff,
            "response_target": {
                "status": "NO_CONFIGURED_RESPONSE_TARGET",
                "target_minutes": None,
                "reason": str(self.policy.get("response_targets", {}).get("reason")),
            },
            "metrics": {
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "owner_routes": owner_routes,
                "runbook_candidates": runbook_guidance["candidate_count"],
                "history_items": len(history),
                "pending_checks": len(pending_checks),
                "timeline_events": len(timeline),
                "handoff_chars": len(json.dumps(handoff, sort_keys=True)),
            },
            "safety": {
                "reported_impact_verified": False,
                "priority_confirmed": False,
                "live_connection_attempted": False,
                "external_ai_call_attempted": False,
                "notification_sent": False,
                "persistence_attempted": False,
                "remediation_attempted": False,
            },
        }
        jsonschema.validate(
            instance=result,
            schema=self.schema,
            format_checker=jsonschema.FormatChecker(),
        )
        return result
