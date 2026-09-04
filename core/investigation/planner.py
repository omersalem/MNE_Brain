"""Deterministic candidate planning; AI remains responsible for diagnosis."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from core.entity.build_entity_index import EntityIndexBuilder


class InvestigationPlanner:
    """Map a question to bounded, immutable P7 read candidates without connecting."""

    _IP = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
    _POLICY = re.compile(r"\b(?:policy|rule|allow|access|internet|blocked|deny|denied)\b", re.I)
    _FIREWALL = re.compile(r"\b(?:fortigate|fortinet|firewall)\b", re.I)
    _LIVE = re.compile(r"\b(?:live|current|currently|now|verify|check|deep)\b", re.I)
    _TARGET_STOP_WORDS = {
        "access", "allow", "answer", "check", "deep", "deny", "denied", "firewall",
        "fortigate", "fortinet", "from", "internet", "live", "policy", "rule", "server",
        "the", "this", "used", "via", "what", "which", "with",
    }

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir).resolve()
        bindings = yaml.safe_load((self.base_dir / "config/p7_device_bindings.yaml").read_text(encoding="utf-8")) or {}
        diagnostics = yaml.safe_load((self.base_dir / "config/p8_diagnostic_catalog.yaml").read_text(encoding="utf-8")) or {}
        self.bindings = {item["binding_id"]: item for item in bindings.get("bindings", [])}
        self.reconciliations = {item["binding_id"]: item for item in diagnostics.get("reconciliations", [])}
        self.entities = {
            item["entity_id"]: item
            for item in EntityIndexBuilder(self.base_dir).build_index(persist=False).get("entities", [])
        }

    def _candidate(self, binding_id: str, *, objective: str, subject_ips: list[str], subject_terms: list[str]) -> dict[str, Any] | None:
        binding = self.bindings.get(binding_id)
        reconciliation = self.reconciliations.get(binding_id, {})
        entity = self.entities.get(str(reconciliation.get("canonical_entity_id") or ""))
        target = str((entity or {}).get("ip") or "").strip()
        if not binding or not entity or not target:
            return None
        if binding.get("scope_status") != "ACTIVE" or binding.get("read_only") is not True:
            return None
        return {
            "binding_id": binding_id,
            "entity_id": entity["entity_id"],
            "entity_name": entity.get("name", entity["entity_id"]),
            "target": target,
            "check_id": binding["check_id"],
            "platform": binding["platform"],
            "objective": objective,
            "subject_ips": subject_ips,
            "subject_terms": subject_terms,
            "read_only": True,
            "operation_included": False,
        }

    def plan(self, question: str) -> dict[str, Any]:
        normalized = " ".join(str(question).split())[:500]
        subject_ips = list(dict.fromkeys(self._IP.findall(normalized)))[:4]
        subject_terms = [
            token for token in dict.fromkeys(re.findall(r"[a-z0-9_.-]+", normalized.casefold()))
            if len(token) >= 3 and token not in self._TARGET_STOP_WORDS and token not in subject_ips
        ][:12]
        candidates: list[dict[str, Any]] = []
        intent = "general_live_verification" if self._LIVE.search(normalized) else "documented_research"
        rationale = "No governed live-read workflow matched this request."

        if self._FIREWALL.search(normalized) and self._POLICY.search(normalized) and (subject_ips or subject_terms):
            intent = "fortigate_policy_lookup"
            rationale = (
                "A named or addressed endpoint and FortiGate policy intent require address-object resolution "
                "followed by policy inspection on the governed edge firewall."
            )
            for binding_id, objective in (
                ("p7-fortigate-edge-addresses", "Resolve the endpoint IP to exact FortiGate address object names."),
                ("p7-fortigate-edge-policies", "Inspect normalized firewall policies for matching source or destination objects."),
            ):
                candidate = self._candidate(binding_id, objective=objective, subject_ips=subject_ips, subject_terms=subject_terms)
                if candidate:
                    candidates.append(candidate)
        else:
            matches = EntityIndexBuilder(self.base_dir).resolve_entity(normalized)
            if len(matches) == 1:
                entity_id = matches[0]["entity_id"]
                matching = []
                for binding_id, reconciliation in self.reconciliations.items():
                    if reconciliation.get("canonical_entity_id") == entity_id:
                        binding = self.bindings.get(binding_id, {})
                        if binding.get("scope_status") == "ACTIVE" and binding.get("read_only") is True:
                            matching.append(binding_id)
                for binding_id in sorted(matching)[:3]:
                    candidate = self._candidate(
                        binding_id,
                        objective=f"Collect current {self.bindings[binding_id]['check_id']} evidence for the exact target.",
                        subject_ips=subject_ips,
                        subject_terms=subject_terms,
                    )
                    if candidate:
                        candidates.append(candidate)
                if candidates:
                    intent = "exact_entity_live_verification"
                    rationale = "The question resolved to one canonical entity with active governed P7 checks."

        return {
            "status": "PLANNED" if candidates else "NO_LIVE_PATH",
            "intent": intent,
            "question": normalized,
            "subject_ips": subject_ips,
            "subject_terms": subject_terms,
            "rationale": rationale,
            "candidates": candidates[:3],
            "maximum_live_checks": 3,
            "writes_allowed": False,
            "operations_included": False,
        }
