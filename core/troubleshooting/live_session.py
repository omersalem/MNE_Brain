"""Owner-gated P8 live collection boundary using existing P7 bindings."""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from core.troubleshooting.engine import P8TroubleshootingEngine


class P8LiveSession:
    """Collect selected P7 baselines and normalize only compact in-memory evidence."""

    def __init__(self, base_dir: Path, collector: Callable[..., dict[str, Any]]):
        self.base_dir = Path(base_dir)
        self.engine = P8TroubleshootingEngine(base_dir=self.base_dir)
        self.collector = collector

    def run(self, request: dict[str, Any], *, owner_proceed: bool) -> dict[str, Any]:
        plan = self.engine.plan(request)
        if not owner_proceed:
            return {"status": "NOT_RUN", "reason": "OWNER_PROCEED_REQUIRED", "plan": plan, "evidence": [], "connection_attempted": False}
        binding_ids = [item["binding_id"] for item in plan["planned_checks"]]
        collected = self.collector(owner_proceed=True, binding_ids=binding_ids)
        timestamp = datetime.now(timezone.utc).isoformat()
        by_id = {item["binding_id"]: item for item in collected.get("results", [])}
        evidence = []
        for check in plan["planned_checks"]:
            item = by_id.get(check["binding_id"], {})
            if not item or item.get("connection_attempted") is not True:
                continue
            status = str(item.get("status", "NOT_RETURNED"))
            material = f"{check['binding_id']}|{check['check_id']}|{timestamp}|{status}"
            evidence.append({
                "evidence_id": "p8-live-" + hashlib.sha256(material.encode()).hexdigest()[:16],
                "binding_id": check["binding_id"],
                "check_id": check["check_id"],
                "collected_at": timestamp,
                "verification_status": "live_verified",
                "trust_level": 5,
                "outcome": "SUCCESS" if status == "SUCCESS" else "FAILED",
                "summary": "Authenticated read-only baseline succeeded." if status == "SUCCESS" else f"Authenticated read-only baseline returned {status}.",
            })
        result = self.engine.plan({**request, "evidence": evidence})
        result["live_session"] = {
            "status": str(collected.get("status", "INCOMPLETE")),
            "owner_reference": "MNE-BRAIN-OWNER",
            "connection_attempted": any(item.get("connection_attempted") for item in collected.get("results", [])),
            "raw_output_included": False,
            "credentials_returned": False,
            "persistence_attempted": False,
            "remediation_attempted": False,
            "policy_restored_to_disabled": True,
        }
        return result
