"""
MNE_Brain Release 2 — Security Review to P8/P9 Troubleshooting Bridge.
Coordinates handoff from security incidents to deterministic P8 investigation planning
and optional P9 deep diagnostics, preserving incident timeline continuity and enabling
Codex/Antigravity analysis over troubleshooting evidence without duplicating engine logic.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.entity.build_entity_index import EntityIndexBuilder
from core.security_review.incidents import IncidentRecord, IncidentStore
from core.security_review.run_store import SecurityReviewRunStore
from core.troubleshooting.engine import P8TroubleshootingEngine
from core.troubleshooting.p9_engine import P9DiagnosticEngine
from core.troubleshooting.p9_live_session import P9LiveSession

logger = logging.getLogger(__name__)


class SecurityTroubleshootingBridge:
    """Bridges detected security incidents to the P8/P9 deterministic troubleshooting subsystem."""

    DEVICE_TO_CANONICAL = {
        "fortigate": "fw-fortigate-edge-01",
        "fortianalyzer": "fw-fortigate-edge-01",
        "f5": "waf-f5-bigip-01",
        "fmc": "fmc-cisco-hq-01",
        "active directory": "dc-windows-ad-01",
        "active_directory": "dc-windows-ad-01",
        "activedirectory": "dc-windows-ad-01",
        "ad": "dc-windows-ad-01",
        "exchange": "ex-windows-mail-01",
    }

    DEVICE_TO_PRIMARY_BINDING = {
        "fortigate": "p7-fortigate-edge",
        "fortianalyzer": "p7-fortigate-edge",
        "f5": "p7-f5",
        "fmc": "p7-fmc-rest",
        "active directory": "p7-ad-primary",
        "active_directory": "p7-ad-primary",
        "activedirectory": "p7-ad-primary",
        "ad": "p7-ad-primary",
        "exchange": "p7-exchange-primary",
        "sophos": "p7-sophos",
    }

    def __init__(
        self,
        base_dir: Optional[Path | str] = None,
        run_store: Optional[SecurityReviewRunStore] = None,
        incident_store: Optional[IncidentStore] = None,
        p8_engine: Optional[P8TroubleshootingEngine] = None,
        p9_engine: Optional[P9DiagnosticEngine] = None,
    ):
        self.base_dir = Path(base_dir or Path(__file__).resolve().parent.parent.parent)
        self.run_store = run_store or SecurityReviewRunStore(self.base_dir / "operations" / "security_review" / "runs")
        self.incident_store = incident_store or self.run_store.incident_store
        self.p8_engine = p8_engine or P8TroubleshootingEngine(self.base_dir)
        self.p9_engine = p9_engine or P9DiagnosticEngine(self.base_dir)
        self.entity_index = EntityIndexBuilder(self.base_dir)

    def resolve_canonical_entity(self, incident: IncidentRecord | Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Resolves exactly one canonical entity from the incident details without guessing."""
        inc_data = incident.to_dict() if isinstance(incident, IncidentRecord) else dict(incident)

        # Try resolving specific targets and affected entities first
        target = inc_data.get("target_identity") or inc_data.get("target")
        if target and str(target).strip() and str(target).strip() != "Perimeter":
            matches = self.entity_index.resolve_entity(str(target).strip())
            if len(matches) == 1:
                return matches[0]

        affected = inc_data.get("affected_entities") or []
        if isinstance(affected, list):
            for aff in affected:
                if aff and str(aff).strip():
                    matches = self.entity_index.resolve_entity(str(aff).strip())
                    if len(matches) == 1:
                        return matches[0]

        # For source device, use governed device-to-canonical mapping
        src_dev = str(inc_data.get("source_device") or "").strip().lower()
        if src_dev:
            for k, canonical_id in self.DEVICE_TO_CANONICAL.items():
                if k in src_dev:
                    matches = self.entity_index.resolve_entity(canonical_id)
                    if matches:
                        return matches[0]
                    return {"entity_id": canonical_id, "name": canonical_id, "source": "catalog_reconciliation"}

            # Direct resolution if not in DEVICE_TO_CANONICAL
            matches = self.entity_index.resolve_entity(src_dev)
            if len(matches) == 1:
                return matches[0]

        # Target-dependent investigations require exactly one canonical entity;
        # ambiguous lookups must return None.
        return None

    def determine_scenario_and_binding(
        self,
        incident: IncidentRecord | Dict[str, Any],
        canonical_entity: Optional[Dict[str, Any]] = None,
        preferred_scenario_id: Optional[str] = None,
        preferred_binding_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Determines the appropriate P8 scenario and primary binding for an incident."""
        inc_data = incident.to_dict() if isinstance(incident, IncidentRecord) else dict(incident)
        title_cat = f"{inc_data.get('category', '')} {inc_data.get('title', '')}".lower()
        dev_lower = str(inc_data.get("source_device", "")).lower()

        # Determine binding
        resolved_binding = None
        if preferred_binding_id and preferred_binding_id in self.p8_engine.bindings:
            if self.p8_engine.bindings[preferred_binding_id].get("scope_status") == "ACTIVE":
                resolved_binding = preferred_binding_id

        if not resolved_binding and canonical_entity:
            entity_id = canonical_entity.get("entity_id")
            for b_id, rec in self.p8_engine.reconciliations.items():
                rec_id = rec.get("canonical_entity_id")
                if rec_id == entity_id or (entity_id in ("dc-windows-ad-01", "dc-mne-ad-01") and rec_id in ("dc-windows-ad-01", "dc-mne-ad-01")):
                    if self.p8_engine.bindings.get(b_id, {}).get("scope_status") == "ACTIVE":
                        resolved_binding = b_id
                        break

        if not resolved_binding:
            for k, b_id in self.DEVICE_TO_PRIMARY_BINDING.items():
                if k in dev_lower:
                    if self.p8_engine.bindings.get(b_id, {}).get("scope_status") == "ACTIVE":
                        resolved_binding = b_id
                        break

        if not resolved_binding:
            raise ValueError(
                f"No active operational binding found for canonical entity '{canonical_entity.get('entity_id') if canonical_entity else dev_lower}'. "
                "Bounded troubleshooting requires an active P7 operational binding."
            )

        # Determine scenario
        if preferred_scenario_id and preferred_scenario_id in self.p8_engine.scenarios:
            scen = self.p8_engine.scenarios[preferred_scenario_id]
            if resolved_binding in scen["primary_bindings"]:
                return preferred_scenario_id, resolved_binding

        # Match scenario based on threat category / title keywords
        if "vpn" in title_cat:
            scen_id = "p8-vpn-access"
            if resolved_binding in self.p8_engine.scenarios[scen_id]["primary_bindings"]:
                return scen_id, resolved_binding

        if any(k in title_cat or k in dev_lower for k in ("ad", "auth", "lockout", "kerberos", "domain", "active directory")):
            scen_id = "p8-dns-ad"
            if resolved_binding in self.p8_engine.scenarios[scen_id]["primary_bindings"]:
                return scen_id, resolved_binding

        if any(k in title_cat for k in ("mail", "exchange", "phishing", "smtp")):
            scen_id = "p8-exchange"
            if resolved_binding in self.p8_engine.scenarios[scen_id]["primary_bindings"]:
                return scen_id, resolved_binding

        if any(k in title_cat for k in ("waf", "web", "http", "exploit")):
            scen_id = "p8-web-publishing"
            if resolved_binding in self.p8_engine.scenarios[scen_id]["primary_bindings"]:
                return scen_id, resolved_binding

        # Default security path scenario
        scen_id = "p8-firewall-security"
        if resolved_binding in self.p8_engine.scenarios[scen_id]["primary_bindings"]:
            return scen_id, resolved_binding

        # Fallback to any scenario that permits this binding
        for s_id, scen in self.p8_engine.scenarios.items():
            if resolved_binding in scen["primary_bindings"]:
                return s_id, resolved_binding

        # If still no match, adjust binding to match p8-firewall-security primary
        fallback_binding = self.p8_engine.scenarios["p8-firewall-security"]["primary_bindings"][0]
        return "p8-firewall-security", fallback_binding

    def start_troubleshooting(
        self,
        fingerprint: str,
        scenario_id: Optional[str] = None,
        binding_id: Optional[str] = None,
        symptom: Optional[str] = None,
        execute_p9: bool = False,
        owner_proceed: bool = False,
        collector_override: Optional[Callable[..., Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Initiates bounded P8 troubleshooting from a security incident.
        Updates the incident timeline and prepares AI handoff payload.
        """
        # Look up incident
        rec = self.incident_store.get_incident(fingerprint)
        if not rec:
            raise ValueError(f"Incident with fingerprint '{fingerprint}' not found.")

        canonical_entity = self.resolve_canonical_entity(rec)
        if not canonical_entity:
            raise ValueError(
                f"Incident '{fingerprint}' does not resolve to an exact canonical entity in infrastructure knowledge. "
                "Bounded troubleshooting requires exactly one canonical target."
            )
        res_scen, res_binding = self.determine_scenario_and_binding(
            rec, canonical_entity, scenario_id, binding_id
        )

        symptom_text = (
            symptom
            or f"[{rec.category}] {rec.title} on {canonical_entity.get('entity_id')}"
        )

        p8_request = {
            "scenario_id": res_scen,
            "binding_id": res_binding,
            "symptom": symptom_text,
            "evidence": [],
        }
        p8_plan = self.p8_engine.plan(p8_request)

        # Append P8 handoff to incident timeline
        planned_check_ids = [c.get("check_id") for c in p8_plan.get("planned_checks", [])]
        self.incident_store.append_timeline_event(
            fingerprint=fingerprint,
            event_type="TROUBLESHOOTING_HANDOFF",
            summary=f"Bounded P8 plan prepared for scenario '{res_scen}' using binding '{res_binding}'.",
            details={
                "scenario_id": res_scen,
                "binding_id": res_binding,
                "canonical_entity_id": canonical_entity.get("entity_id") if canonical_entity else None,
                "planned_checks": planned_check_ids,
            },
        )

        p9_result = None
        if execute_p9 and owner_proceed:
            p9_scen = res_scen.replace("p8-", "p9-") if res_scen.startswith("p8-") else res_scen
            if p9_scen in self.p9_engine.scenarios and res_binding not in self.p9_engine.scenarios[p9_scen]["primary_bindings"]:
                for s_id, s_data in self.p9_engine.scenarios.items():
                    if res_binding in s_data.get("primary_bindings", []):
                        p9_scen = s_id
                        break
            if collector_override is None:
                p9_result = {
                    "status": "PREPARED_NOT_EXECUTED",
                    "scenario_id": p9_scen,
                    "binding_id": res_binding,
                    "checks_executed": 0,
                    "reason": "Live P9 collector not provided. Live transport remains disabled at rest.",
                    "collection_results": [],
                    "failed_checks": [],
                }
            else:
                session = P9LiveSession(self.base_dir, collector=collector_override)
                p9_request = {
                    "scenario_id": p9_scen,
                    "binding_id": res_binding,
                    "symptom": symptom_text,
                }
                p9_result = session.run(p9_request, owner_proceed=True)
                p9_result["checks_executed"] = len(p9_result.get("collection_results", []))

                self.incident_store.append_timeline_event(
                    fingerprint=fingerprint,
                    event_type="TROUBLESHOOTING_EXECUTION",
                    summary=f"P9 deep diagnostic execution completed with status '{p9_result.get('status')}'.",
                    details={
                        "status": p9_result.get("status"),
                        "failed_checks": p9_result.get("failed_checks", []),
                        "checks_attempted": [c.get("check_id") for c in p9_result.get("collection_results", [])],
                    },
                )

        ai_handoff = dict(p8_plan.get("ai_handoff") or {})
        prompt_lines = [
            f"Security Incident Investigation Handoff: {rec.title} ({rec.display_id})",
            f"Target Canonical Entity: {canonical_entity.get('entity_id') if canonical_entity else 'Unknown'}",
            f"Scenario: {res_scen} | Operational Binding: {res_binding}",
            f"Attacker: {rec.attacker_identity or 'Unknown'} | Category: {rec.category}",
            f"Planned Checks: {', '.join(planned_check_ids)}",
            f"Instruction: {ai_handoff.get('reasoning_instruction', 'Evaluate evidence and recommend diagnostic steps.')}",
        ]
        ai_handoff["suggested_ai_prompt"] = "\n".join(prompt_lines)

        return {
            "status": "SUCCESS",
            "fingerprint": fingerprint,
            "incident": {
                "display_id": rec.display_id,
                "title": rec.title,
                "category": rec.category,
                "severity": rec.current_severity,
                "attacker_identity": rec.attacker_identity,
                "target_identity": rec.target_identity,
                "source_device": rec.source_device,
            },
            "canonical_entity": canonical_entity,
            "target_canonical": canonical_entity.get("entity_id") if canonical_entity else None,
            "scenario": res_scen,
            "scenario_id": res_scen,
            "binding": res_binding,
            "binding_id": res_binding,
            "p8_plan": p8_plan,
            "p9_result": p9_result,
            "ai_handoff": ai_handoff,
        }

    def format_ai_troubleshooting_instruction(self, handoff_result: Dict[str, Any]) -> str:
        """Constructs an evidence-bounded instruction for continuing an AI troubleshooting turn."""
        inc = handoff_result.get("incident", {})
        p8 = handoff_result.get("p8_plan", {})
        checks = [c.get("objective") for c in p8.get("planned_checks", [])]

        return (
            f"Continuing troubleshooting for incident {inc.get('display_id')} ({inc.get('title')}).\n"
            f"Canonical Target: {handoff_result.get('canonical_entity', {}).get('entity_id')}\n"
            f"P8 Scenario: {handoff_result.get('scenario_id')} (Binding: {handoff_result.get('binding_id')})\n"
            f"Planned Diagnostics: {', '.join(checks)}\n\n"
            "Analyze the planned checks and incident observations. Recommend the exact next diagnostic step "
            "and state what questions remain unresolved."
        )
