#!/usr/bin/env python3
"""Run one approved two-check P2 -> P3 -> P4 read-only session."""

import json
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.incidents.case_manager import IncidentCaseManager
from core.orchestration.incident_orchestrator import IncidentOrchestrator
from core.verification.live_verify import LiveVerificationEngine
from core.verification.readonly_adapter import ReadOnlyVerificationAdapter
from integrations.fortigate.plink_transport import PinnedPlinkFortiGateTransport


PROFILE = "fortigate_edge"
ENTITY_ID = "fw-fortigate-edge-01"
SCOPE_REFERENCE = "P3-P4-LIVE-EVIDENCE-SESSION-2026-08-16"
QUESTION = f"Assess current troubleshooting evidence for {ENTITY_ID}"


def _credential_reference() -> str:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return ""
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        if raw_line.startswith("FORTIGATE_CREDENTIAL_REF="):
            return raw_line.split("=", 1)[1].strip()
    return ""


def collect_live_evidence() -> dict[str, Any]:
    """Collect only the two checks declared in the approved P2 profile."""
    adapter_id = "fortigate_ssh_readonly"
    adapter = ReadOnlyVerificationAdapter(
        adapter_id,
        PinnedPlinkFortiGateTransport(base_dir=BASE_DIR),
        simulation_mode=False,
        base_dir=BASE_DIR,
    )
    engine = LiveVerificationEngine(base_dir=BASE_DIR, adapters={adapter_id: adapter})
    return engine.execute_live_verification(
        PROFILE,
        check_id=None,
        authorized=True,
        entity_id=ENTITY_ID,
        scope_reference=SCOPE_REFERENCE,
        credential_reference=_credential_reference(),
    )


def compose_session(verification_result: dict[str, Any]) -> dict[str, Any]:
    """Pass the in-memory P2 envelope through P3 and P4 without persistence."""
    investigation = IncidentOrchestrator(base_dir=BASE_DIR).investigate(
        QUESTION,
        verification_result=verification_result,
    )
    incident_case = IncidentCaseManager(base_dir=BASE_DIR).build_case(
        QUESTION,
        verification_result=verification_result,
    )
    records = verification_result.get("telemetry_results", [])
    return {
        "session_scope_reference": SCOPE_REFERENCE,
        "p2": {
            "status": verification_result.get("status"),
            "entity_id": verification_result.get("entity_id"),
            "trust_level": verification_result.get("trust_level"),
            "checks_attempted": verification_result.get("checks_attempted", 0),
            "checks_executed": verification_result.get("checks_executed", 0),
            "evidence": [
                {
                    "evidence_id": record.get("evidence_id"),
                    "check_id": record.get("verification_check_id"),
                    "observed_at": record.get("observed_at"),
                    "expires_at": record.get("expires_at"),
                    "content_sha256": record.get("content_sha256"),
                }
                for record in records
            ],
            "connection_attempted": verification_result.get("connection_attempted", False),
            "raw_output_returned": verification_result.get("raw_output_returned", False),
            "credential_returned": verification_result.get("credential_returned", False),
            "persistence": verification_result.get("persistence"),
            "failures": verification_result.get("failures", []),
        },
        "p3": {
            "investigation_id": investigation.get("investigation_id"),
            "status": investigation.get("status"),
            "reasoning_status": investigation.get("reasoning", {}).get("reasoning_status"),
            "conclusive_root_cause": investigation.get("reasoning", {}).get(
                "conclusive_root_cause"
            ),
            "accepted_evidence_refs": investigation.get("reasoning", {}).get(
                "accepted_evidence_refs", []
            ),
            "accepted_evidence": investigation.get("metrics", {}).get("accepted_evidence", 0),
            "unknowns": investigation.get("evidence_pack", {}).get("unknowns", []),
            "next_check_ids": [item.get("check_id") for item in investigation.get("next_checks", [])],
            "handoff_chars": investigation.get("metrics", {}).get("handoff_chars", 0),
            "safety": investigation.get("safety", {}),
        },
        "p4": {
            "case_id": incident_case.get("case_id"),
            "case_state": incident_case.get("case_state"),
            "priority": incident_case.get("priority", {}).get("classification"),
            "primary_owner": incident_case.get("ownership", {}).get("primary", {}).get("team"),
            "accepted_evidence_refs": incident_case.get("investigation", {})
            .get("reasoning", {})
            .get("accepted_evidence_refs", []),
            "handoff_chars": incident_case.get("metrics", {}).get("handoff_chars", 0),
            "safety": incident_case.get("safety", {}),
        },
    }


if __name__ == "__main__":
    collected = collect_live_evidence()
    summary = compose_session(collected)
    print(json.dumps(summary, indent=2))
    success = collected.get("status") in {"SUCCESS", "PARTIAL"}
    sys.exit(0 if success else 1)
