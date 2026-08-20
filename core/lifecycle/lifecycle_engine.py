#!/usr/bin/env python3
"""Attributable knowledge-drift review without automatic canonical mutation."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


class KnowledgeLifecycleEngine:
    """Compare accepted facts, stage review proposals, and never edit canonical notes."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.knowledge_dir = self.base_dir / "knowledge"
        self.review_queue_file = self.base_dir / "operations" / "discovery" / "review_queue.json"
        self.history_file = self.base_dir / "operations" / "discovery" / "verification_history.json"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _canonical_path(self, canonical_file: str) -> Path:
        candidate = (self.base_dir / canonical_file).resolve()
        knowledge_root = self.knowledge_dir.resolve()
        try:
            candidate.relative_to(knowledge_root)
        except ValueError as exc:
            raise ValueError("Canonical files must be located beneath knowledge/.") from exc
        return candidate

    @staticmethod
    def _normalise_facts(value: Any, *, field_name: str) -> dict[str, str]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError(f"{field_name} must be a mapping.")
        facts: dict[str, str] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise ValueError(f"{field_name} keys must be non-empty strings.")
            if not isinstance(item, (str, int, float, bool)):
                raise ValueError(f"{field_name}[{key!r}] must be a scalar value.")
            facts[key] = str(item)
        return facts

    def _load_canonical(self, canonical_file: str) -> tuple[Path, dict[str, Any]]:
        canonical_path = self._canonical_path(canonical_file)
        if not canonical_path.exists():
            raise FileNotFoundError(f"Canonical file {canonical_file!r} was not found.")
        text = canonical_path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            raise ValueError("Canonical file has no YAML frontmatter.")
        parts = text.split("---", 2)
        if len(parts) < 3:
            raise ValueError("Canonical file frontmatter is incomplete.")
        metadata = yaml.safe_load(parts[1]) or {}
        if not isinstance(metadata, dict):
            raise ValueError("Canonical frontmatter must be a mapping.")
        return canonical_path, metadata

    @staticmethod
    def _validate_live_evidence(
        evidence: Any, expected_entity_id: str
    ) -> tuple[dict[str, Any] | None, str | None]:
        if not isinstance(evidence, dict):
            return None, "Evidence must be a mapping, not free-form telemetry text."
        required_fields = (
            "entity_id",
            "source_file",
            "source",
            "evidence_status",
            "trust_level",
            "observed_at",
            "evidence_refs",
            "verification_target",
            "verification_check_id",
            "verification_outcome",
        )
        missing_fields = [field for field in required_fields if not evidence.get(field)]
        if missing_fields:
            return None, f"Missing evidence fields: {', '.join(missing_fields)}."
        if evidence["entity_id"] != expected_entity_id:
            return None, "Evidence entity_id does not match the requested canonical entity."
        if evidence["evidence_status"] != "live_verified":
            return None, "Evidence status is not live_verified."
        if evidence["trust_level"] != 5:
            return None, "Evidence trust level is not 5."
        if evidence["verification_outcome"] != "success":
            return None, "Evidence verification outcome is not success."
        if not isinstance(evidence["evidence_refs"], list) or not evidence["evidence_refs"]:
            return None, "Evidence references must be a non-empty list."
        try:
            observed_at = datetime.fromisoformat(str(evidence["observed_at"]).replace("Z", "+00:00"))
        except ValueError:
            return None, "Evidence observed_at is not an ISO-8601 timestamp."
        if observed_at.tzinfo is None or observed_at.astimezone(timezone.utc) > datetime.now(timezone.utc):
            return None, "Evidence observed_at must be timezone-aware and not in the future."
        try:
            observed_facts = KnowledgeLifecycleEngine._normalise_facts(
                evidence.get("observed_facts"), field_name="observed_facts"
            )
        except ValueError as exc:
            return None, str(exc)
        return {
            "evidence_refs": sorted(set(str(item) for item in evidence["evidence_refs"])),
            "observed_facts": observed_facts,
        }, None

    @staticmethod
    def _report(
        *,
        status: str,
        entity_id: str,
        canonical_file: str,
        reason: str,
        canonical_status: str | None = None,
        drift_items: list[dict[str, Any]] | None = None,
        accepted_evidence_refs: list[str] | None = None,
        invalid_evidence: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "status": status,
            "entity_id": entity_id,
            "canonical_file": canonical_file,
            "canonical_status": canonical_status,
            "drift_detected": status == "DRIFT_DETECTED",
            "drift_items": drift_items or [],
            "accepted_evidence_refs": accepted_evidence_refs or [],
            "invalid_evidence": invalid_evidence or [],
            "reason": reason,
            "created_at": KnowledgeLifecycleEngine._now(),
            "persistence": "NOT_REQUESTED",
        }

    def detect_knowledge_drift(
        self,
        entity_id: str,
        canonical_file: str,
        live_evidence: dict[str, Any] | list[dict[str, Any]] | Any,
        *,
        persist: bool = False,
    ) -> dict[str, Any]:
        """Compare declared facts only when both sides have accepted provenance.

        The default is in-memory only. ``persist=True`` can append a review
        proposal and history record but never modifies canonical knowledge.
        """
        try:
            _, canonical_metadata = self._load_canonical(canonical_file)
        except (FileNotFoundError, ValueError) as exc:
            return self._report(
                status="CANONICAL_UNAVAILABLE",
                entity_id=entity_id,
                canonical_file=canonical_file,
                reason=str(exc),
            )

        canonical_status = str(canonical_metadata.get("knowledge_status", "unverified"))
        if canonical_metadata.get("id") != entity_id:
            return self._report(
                status="CANONICAL_ENTITY_MISMATCH",
                entity_id=entity_id,
                canonical_file=canonical_file,
                canonical_status=canonical_status,
                reason="Canonical note id does not match the requested entity.",
            )
        if canonical_status != "live_verified":
            return self._report(
                status="CANONICAL_NOT_ACCEPTED",
                entity_id=entity_id,
                canonical_file=canonical_file,
                canonical_status=canonical_status,
                reason="Canonical knowledge is not live_verified and cannot be drift-compared.",
            )
        try:
            canonical_facts = self._normalise_facts(
                canonical_metadata.get("facts"), field_name="canonical facts"
            )
        except ValueError as exc:
            return self._report(
                status="CANONICAL_UNAVAILABLE",
                entity_id=entity_id,
                canonical_file=canonical_file,
                canonical_status=canonical_status,
                reason=str(exc),
            )
        if not canonical_facts:
            return self._report(
                status="NO_COMPARABLE_FACTS",
                entity_id=entity_id,
                canonical_file=canonical_file,
                canonical_status=canonical_status,
                reason="Canonical knowledge has no declared facts for drift comparison.",
            )

        evidence_items = live_evidence if isinstance(live_evidence, list) else [live_evidence]
        accepted_items: list[dict[str, Any]] = []
        invalid_evidence: list[str] = []
        for evidence in evidence_items:
            accepted, reason = self._validate_live_evidence(evidence, entity_id)
            if accepted is None:
                invalid_evidence.append(reason or "Invalid evidence.")
            else:
                accepted_items.append(accepted)
        if not accepted_items:
            return self._report(
                status="INSUFFICIENT_LIVE_EVIDENCE",
                entity_id=entity_id,
                canonical_file=canonical_file,
                canonical_status=canonical_status,
                reason="No attributable Level-5 live evidence was accepted for comparison.",
                invalid_evidence=invalid_evidence,
            )

        observed_values: dict[str, set[str]] = {}
        accepted_evidence_refs: set[str] = set()
        for item in accepted_items:
            accepted_evidence_refs.update(item["evidence_refs"])
            for fact_name, fact_value in item["observed_facts"].items():
                observed_values.setdefault(fact_name, set()).add(fact_value)
        conflicting_facts = sorted(
            fact_name for fact_name, values in observed_values.items() if len(values) > 1
        )
        if conflicting_facts:
            return self._report(
                status="CONFLICTING_LIVE_EVIDENCE",
                entity_id=entity_id,
                canonical_file=canonical_file,
                canonical_status=canonical_status,
                reason="Accepted evidence disagrees on: " + ", ".join(conflicting_facts),
                accepted_evidence_refs=sorted(accepted_evidence_refs),
                invalid_evidence=invalid_evidence,
            )

        common_facts = sorted(set(canonical_facts).intersection(observed_values))
        if not common_facts:
            return self._report(
                status="NO_COMPARABLE_FACTS",
                entity_id=entity_id,
                canonical_file=canonical_file,
                canonical_status=canonical_status,
                reason="Accepted evidence contains no facts declared in canonical knowledge.",
                accepted_evidence_refs=sorted(accepted_evidence_refs),
                invalid_evidence=invalid_evidence,
            )

        drift_items = [
            {
                "fact": fact_name,
                "canonical_value": canonical_facts[fact_name],
                "observed_value": next(iter(observed_values[fact_name])),
            }
            for fact_name in common_facts
            if canonical_facts[fact_name] != next(iter(observed_values[fact_name]))
        ]
        status = "DRIFT_DETECTED" if drift_items else "NO_DRIFT"
        report = self._report(
            status=status,
            entity_id=entity_id,
            canonical_file=canonical_file,
            canonical_status=canonical_status,
            reason=(
                "Accepted live evidence differs from declared canonical facts."
                if drift_items
                else "Accepted live evidence matches all comparable canonical facts."
            ),
            drift_items=drift_items,
            accepted_evidence_refs=sorted(accepted_evidence_refs),
            invalid_evidence=invalid_evidence,
        )
        if persist:
            report["persistence"] = self._persist_review_state(report)
        return report

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default

    def _persist_review_state(self, report: dict[str, Any]) -> str:
        """Persist append-only history and an optional manual-review proposal."""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        history = self._read_json(self.history_file, {"events": []})
        if not isinstance(history, dict):
            history = {"events": []}
        events = history.get("events")
        if not isinstance(events, list):
            events = []
        events.append(
            {
                "entity_id": report["entity_id"],
                "canonical_file": report["canonical_file"],
                "status": report["status"],
                "created_at": report["created_at"],
                "evidence_refs": report["accepted_evidence_refs"],
            }
        )
        self.history_file.write_text(
            json.dumps({"events": events}, indent=2), encoding="utf-8"
        )
        if report["status"] != "DRIFT_DETECTED":
            return "HISTORY_RECORDED"

        self.review_queue_file.parent.mkdir(parents=True, exist_ok=True)
        queue = self._read_json(self.review_queue_file, [])
        if not isinstance(queue, list):
            queue = []
        fingerprint_input = json.dumps(
            {
                "entity_id": report["entity_id"],
                "canonical_file": report["canonical_file"],
                "drift_items": report["drift_items"],
                "evidence_refs": report["accepted_evidence_refs"],
            },
            sort_keys=True,
        )
        fingerprint = hashlib.sha256(fingerprint_input.encode("utf-8")).hexdigest()
        existing = next(
            (item for item in queue if item.get("fingerprint") == fingerprint), None
        )
        if existing is None:
            queue.append(
                {
                    "proposal_id": f"prop-{fingerprint[:12]}",
                    "fingerprint": fingerprint,
                    "entity_id": report["entity_id"],
                    "canonical_file": report["canonical_file"],
                    "proposed_changes": report["drift_items"],
                    "evidence_refs": report["accepted_evidence_refs"],
                    "status": "PENDING_OWNER_REVIEW",
                    "created_at": report["created_at"],
                    "auto_overwrite_allowed": False,
                }
            )
            self.review_queue_file.write_text(json.dumps(queue, indent=2), encoding="utf-8")
            return "HISTORY_RECORDED_AND_PROPOSAL_STAGED"
        return "HISTORY_RECORDED_AND_EXISTING_PROPOSAL_RETAINED"

    def promote_to_canonical(
        self, proposal_id: str, *, explicit_owner_instruction: bool = False
    ) -> dict[str, Any]:
        """Record sole-owner review for a manual update; never edit the note."""
        if explicit_owner_instruction is not True:
            return {
                "promoted": False,
                "owner_reviewed_for_manual_promotion": False,
                "reason": "Explicit instruction from MNE-BRAIN-OWNER is required.",
            }
        queue = self._read_json(self.review_queue_file, [])
        if not isinstance(queue, list):
            return {
                "promoted": False,
                "owner_reviewed_for_manual_promotion": False,
                "reason": "Review queue is unavailable.",
            }
        proposal = next((item for item in queue if item.get("proposal_id") == proposal_id), None)
        if proposal is None:
            return {
                "promoted": False,
                "owner_reviewed_for_manual_promotion": False,
                "reason": f"Proposal ID {proposal_id!r} was not found.",
            }
        if proposal.get("status") != "PENDING_OWNER_REVIEW":
            return {
                "promoted": False,
                "owner_reviewed_for_manual_promotion": False,
                "reason": "Proposal is not pending sole-owner review.",
            }

        proposal["status"] = "OWNER_REVIEWED_FOR_MANUAL_PROMOTION"
        proposal["reviewed_by"] = "MNE-BRAIN-OWNER"
        proposal["reviewed_at"] = self._now()
        self.review_queue_file.write_text(json.dumps(queue, indent=2), encoding="utf-8")
        return {
            "promoted": False,
            "owner_reviewed_for_manual_promotion": True,
            "proposal_id": proposal_id,
            "entity_id": proposal["entity_id"],
            "canonical_file": proposal["canonical_file"],
            "reviewed_by": proposal["reviewed_by"],
            "reason": "Canonical knowledge was not changed; the sole owner must apply the manual update explicitly.",
        }
