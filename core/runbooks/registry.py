#!/usr/bin/env python3
"""Deterministic, metadata-only runbook selection and coverage auditing."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import jsonschema
import yaml


class RunbookRegistry:
    """Select bounded troubleshooting guidance without executing runbook content."""

    MODE = "OWNER_REVIEWED_CONTEXT_SELECTION"
    OWNER_REFERENCE = "MNE-BRAIN-OWNER"
    _COVERAGE_TYPES = {"domain_troubleshooting", "verification_pilot"}

    def __init__(self, base_dir: Path | None = None, runbooks_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.runbooks_dir = runbooks_dir or self.base_dir / "intelligence" / "runbooks"
        self.config_path = self.base_dir / "config" / "p5_runbook_policy.yaml"
        self.schema_path = self.base_dir / "00_meta" / "schemas" / "runbook.schema.json"
        self.config = self._load_mapping(self.config_path)
        self.schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        self.limits = self.config.get("limits", {})
        if self.config.get("owner_reference") != self.OWNER_REFERENCE:
            raise ValueError("P5 owner_reference must be MNE-BRAIN-OWNER")
        self._registry_cache: dict[str, Any] | None = None

    @staticmethod
    def _load_mapping(path: Path) -> dict[str, Any]:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(value, dict):
            raise ValueError(f"{path.name} must contain a mapping")
        return value

    @staticmethod
    def _metadata(path: Path) -> dict[str, Any]:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            raise ValueError(f"Runbook {path.name} has no governed frontmatter")
        parts = text.split("---", 2)
        if len(parts) < 3:
            raise ValueError(f"Runbook {path.name} has malformed frontmatter")
        metadata = yaml.safe_load(parts[1]) or {}
        if not isinstance(metadata, dict):
            raise ValueError(f"Runbook {path.name} frontmatter must contain a mapping")
        return metadata

    def build_registry(self) -> dict[str, Any]:
        if self._registry_cache is not None:
            return deepcopy(self._registry_cache)
        runbooks: list[dict[str, Any]] = []
        seen: dict[str, str] = {}
        for path in sorted(self.runbooks_dir.glob("*.md")):
            metadata = self._metadata(path)
            jsonschema.validate(
                instance=metadata,
                schema=self.schema,
                format_checker=jsonschema.FormatChecker(),
            )
            runbook_id = metadata["runbook_id"]
            if runbook_id in seen:
                raise ValueError(
                    f"Duplicate runbook ID {runbook_id} in {seen[runbook_id]} and {path.name}"
                )
            seen[runbook_id] = path.name
            record = dict(metadata)
            try:
                record["source_file"] = path.relative_to(self.base_dir).as_posix()
            except ValueError:
                record["source_file"] = path.name
            runbooks.append(record)
        self._registry_cache = {
            "mode": self.MODE,
            "total_runbooks": len(runbooks),
            "runbooks": sorted(runbooks, key=lambda item: item["runbook_id"]),
            "persistence_attempted": False,
        }
        return deepcopy(self._registry_cache)

    def _score(self, runbook: dict[str, Any], target: dict[str, Any]) -> tuple[int, list[str]]:
        weights = self.config.get("selection_weights", {})
        score = 0
        basis: list[str] = []
        if target["entity_id"] in runbook.get("scope_entity_ids", []):
            score += int(weights.get("exact_entity", 100))
            basis.append("exact_entity")
        matching_services = sorted(
            set(target.get("services", [])).intersection(runbook.get("scope_services", []))
        )
        if matching_services:
            score += len(matching_services) * int(weights.get("matching_service", 10))
            basis.extend(f"service:{service}" for service in matching_services)
        if (
            target.get("category") in runbook.get("scope_categories", [])
            and (
                runbook.get("category_fallback_allowed") is True
                or bool(matching_services)
                or "exact_entity" in basis
            )
        ):
            score += int(weights.get("matching_category", 20))
            basis.append(f"category:{target['category']}")
        if score and runbook.get("runbook_type") == "domain_troubleshooting":
            score += int(weights.get("domain_runbook", 5))
        status = runbook.get("status")
        if score and status == "offline_validated":
            score += int(weights.get("offline_validated", 2))
        elif score and status == "operationally_reviewed":
            score += int(weights.get("operationally_reviewed", 4))
        return score, basis

    def select_for_target(self, target: Any) -> dict[str, Any]:
        if not isinstance(target, dict) or not all(
            isinstance(target.get(field), str) and target.get(field)
            for field in ("entity_id", "category")
        ):
            return self._empty_selection("An exact canonical target is required.")
        services = target.get("services", [])
        if not isinstance(services, list) or any(not isinstance(item, str) for item in services):
            return self._empty_selection("Target services are malformed.")

        operational_status = self.config.get("lifecycle", {}).get(
            "operational_status", "operationally_reviewed"
        )
        candidates: list[dict[str, Any]] = []
        for runbook in self.build_registry()["runbooks"]:
            score, match_basis = self._score(runbook, target)
            if score <= 0:
                continue
            operational = runbook["status"] == operational_status
            coverage_eligible = runbook["runbook_type"] in self._COVERAGE_TYPES
            candidates.append(
                {
                    "runbook_id": runbook["runbook_id"],
                    "title": runbook["title"],
                    "version": runbook["version"],
                    "status": runbook["status"],
                    "runbook_type": runbook["runbook_type"],
                    "owner_team": runbook["owner_team"],
                    "review_sources": runbook["review_sources"][:3],
                    "operational_boundary": runbook["operational_boundary"],
                    "source_file": runbook["source_file"],
                    "score": score,
                    "match_basis": match_basis,
                    "evidence_objectives": runbook["evidence_objectives"][:5],
                    "stop_conditions": runbook["stop_conditions"][:3],
                    "owner_review_complete": operational,
                    "domain_coverage_eligible": coverage_eligible,
                    "operational_use_allowed": operational and coverage_eligible,
                }
            )
        limit = int(self.limits.get("max_candidates", 3))
        selected = sorted(candidates, key=lambda item: (-item["score"], item["runbook_id"]))[:limit]
        if not selected:
            return self._empty_selection("No governed runbook matches the exact target metadata.")
        operational_available = any(item["operational_use_allowed"] for item in selected)
        result = {
            "mode": self.MODE,
            "owner_reference": self.OWNER_REFERENCE,
            "target_entity_id": target["entity_id"],
            "selection_status": (
                "OWNER_REVIEWED_GUIDANCE_AVAILABLE"
                if operational_available
                else "CONTEXT_ONLY_NOT_OPERATIONALLY_REVIEWED"
            ),
            "candidates": selected,
            "candidate_count": len(selected),
            "operational_use_allowed": operational_available,
            "body_included": False,
            "live_connection_attempted": False,
            "external_ai_call_attempted": False,
            "notification_sent": False,
            "persistence_attempted": False,
            "remediation_attempted": False,
            "reason": (
                "At least one selected domain runbook has completed sole-owner procedure review; live state remains unverified."
                if operational_available
                else "No selected domain runbook has completed sole-owner procedure review."
            ),
        }
        max_chars = int(self.limits.get("max_guidance_chars", 3000))
        while len(json.dumps(result, sort_keys=True)) > max_chars and result["candidates"]:
            result["candidates"].pop()
            result["candidate_count"] = len(result["candidates"])
        if not result["candidates"]:
            return self._empty_selection("Matching guidance exceeded the configured context budget.")
        return result

    def _empty_selection(self, reason: str) -> dict[str, Any]:
        return {
            "mode": self.MODE,
            "owner_reference": self.OWNER_REFERENCE,
            "target_entity_id": None,
            "selection_status": "NO_MATCH",
            "candidates": [],
            "candidate_count": 0,
            "operational_use_allowed": False,
            "body_included": False,
            "live_connection_attempted": False,
            "external_ai_call_attempted": False,
            "notification_sent": False,
            "persistence_attempted": False,
            "remediation_attempted": False,
            "reason": reason,
        }

    def coverage_report(self, entities: list[dict[str, Any]]) -> dict[str, Any]:
        context_covered: list[str] = []
        operationally_covered: list[str] = []
        gaps: list[str] = []
        for entity in entities:
            selection = self.select_for_target(entity)
            entity_id = str(entity.get("entity_id", ""))
            if selection["candidate_count"]:
                context_covered.append(entity_id)
            else:
                gaps.append(entity_id)
            if selection["operational_use_allowed"]:
                operationally_covered.append(entity_id)
        total = len(entities)
        operational_complete = total > 0 and len(operationally_covered) == total
        return {
            "mode": self.MODE,
            "owner_reference": self.OWNER_REFERENCE,
            "total_entities": total,
            "context_covered_entities": len(context_covered),
            "context_coverage_percent": round((len(context_covered) / total * 100) if total else 0, 2),
            "operationally_covered_entities": len(operationally_covered),
            "operational_coverage_percent": round(
                (len(operationally_covered) / total * 100) if total else 0, 2
            ),
            "context_gaps": gaps,
            "operational_gaps": sorted(
                entity["entity_id"]
                for entity in entities
                if entity["entity_id"] not in operationally_covered
            ),
            "operational_runbook_readiness": operational_complete,
            "production_readiness_claimed": False,
            "persistence_attempted": False,
        }
