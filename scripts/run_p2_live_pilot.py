#!/usr/bin/env python3
"""Run the one-command P2 FortiGate edge pilot through MNE_Brain."""

import argparse
import json
import re
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.verification.live_verify import LiveVerificationEngine
from core.verification.readonly_adapter import ReadOnlyVerificationAdapter
from integrations.fortigate.plink_transport import PinnedPlinkFortiGateTransport


def _read_local_reference() -> str:
    for raw_line in (BASE_DIR / ".env").read_text(encoding="utf-8").splitlines():
        if raw_line.startswith("FORTIGATE_CREDENTIAL_REF="):
            return raw_line.split("=", 1)[1].strip()
    return ""


APPROVED_SCOPES = {
    "system_status": "P2-LIVE-EDGE-SYSTEM-STATUS-2026-08-16",
    "interface_stats": "P2-LIVE-EDGE-INTERFACE-STATS-2026-08-16",
}


def run_live_pilot(check_id: str = "system_status") -> dict:
    if check_id not in APPROVED_SCOPES:
        raise ValueError("check_id is not approved by the live pilot runner")
    transport = PinnedPlinkFortiGateTransport(base_dir=BASE_DIR)
    adapter = ReadOnlyVerificationAdapter(
        "fortigate_ssh_readonly",
        transport,
        simulation_mode=False,
        base_dir=BASE_DIR,
    )
    engine = LiveVerificationEngine(
        base_dir=BASE_DIR,
        adapters={"fortigate_ssh_readonly": adapter},
    )
    return engine.execute_live_verification(
        "fortigate_edge",
        check_id=check_id,
        authorized=True,
        entity_id="fw-fortigate-edge-01",
        scope_reference=APPROVED_SCOPES[check_id],
        credential_reference=_read_local_reference(),
    )


def _minimized_content_summary(item: dict) -> dict:
    content = str(item.get("content", ""))
    status_values = re.findall(r"(?im)^\s*status:\s*(up|down)\s*$", content)
    interface_sections = re.findall(r"(?m)^\s*==\[[^\]]+\]", content)
    return {
        "check_id": item.get("verification_check_id"),
        "content_chars": len(content),
        "line_count": len(content.splitlines()),
        "interface_sections": len(interface_sections),
        "status_up": sum(value.casefold() == "up" for value in status_values),
        "status_down": sum(value.casefold() == "down" for value in status_values),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-id",
        choices=tuple(APPROVED_SCOPES),
        default="system_status",
    )
    arguments = parser.parse_args()
    result = run_live_pilot(arguments.check_id)
    evidence = result.get("telemetry_results", [])
    summary = {
        "status": result.get("status"),
        "entity_id": result.get("entity_id"),
        "trust_level": result.get("trust_level"),
        "checks_executed": result.get("checks_executed", 0),
        "checks_attempted": result.get("checks_attempted", 0),
        "connection_attempted": result.get("connection_attempted", False),
        "evidence_ids": [item.get("evidence_id") for item in evidence],
        "observed_at": [item.get("observed_at") for item in evidence],
        "expires_at": [item.get("expires_at") for item in evidence],
        "content_sha256": [item.get("content_sha256") for item in evidence],
        "content_summary": [_minimized_content_summary(item) for item in evidence],
        "raw_output_returned": result.get("raw_output_returned", False),
        "credential_returned": result.get("credential_returned", False),
        "persistence": result.get("persistence"),
        "failures": result.get("failures", []),
    }
    print(json.dumps(summary, indent=2))
    sys.exit(0 if result.get("status") == "SUCCESS" else 1)
