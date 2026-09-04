#!/usr/bin/env python3
"""Run the Owner Direct control-plane contract with a non-network fixture."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from core.infrastructure.owner_direct import OwnerDirectService


class OfflineAdapter:
    def read(self, request: dict) -> dict:
        if request.get("postcheck"):
            return {"status": "SUCCESS", "identity": "SHA256:offline-owner-direct"}
        return {"status": "SUCCESS", "reachable": True, "authentication": "SUCCESS", "identity": "SHA256:offline-owner-direct", "facts": {"model": "fixture", "version": "offline"}}

    def write(self, request: dict) -> dict:
        return {"status": "COMMITTED", "submitted": True}


def main() -> int:
    service = OwnerDirectService(BASE, adapters={"ssh": OfflineAdapter()})
    service.bindings = []
    discovery = service.discover(entity_id="fw-fortigate-hq-01", protocol="ssh", operation="get system status")
    plan = service.prepare_write(
        entity_id="fw-fortigate-hq-01", protocol="ssh", operations=["configure firewall address OWNER_DIRECT_OFFLINE"],
        intended_change="Create the offline fixture address object.", expected_impact="No live impact; fixture only.", downtime_risk="None.",
        blast_radius="The offline fixture only.", prechecks=["Fixture is loaded."], postchecks=["Fixture returns success."], owner_requested=True,
    )
    result = service.confirm_write(plan["plan_id"], owner_session_digest="a" * 64)
    passed = discovery["identity_result"] == "IDENTITY_UNVERIFIED" and result["status"] == "COMMITTED" and result["postcheck_status"] == "SUCCESS"
    print(json.dumps({"status": "PASSED" if passed else "FAILED", "mode": "OWNER_DIRECT", "network_attempted": False, "discovery_evidence_id": discovery["evidence_id"], "write_submitted_to_fixture": result["submitted"], "postcheck_status": result["postcheck_status"], "secrets_returned": False}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
