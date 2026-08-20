#!/usr/bin/env python3
"""Exercise all P9 families with attributable in-memory fixtures and no connections."""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.troubleshooting.p9_engine import P9DiagnosticEngine


CASES = [
    ("p9-branch-outage", "p7-fortigate-nablus", "branch down"),
    ("p9-vpn-access", "p7-fortigate-edge", "VPN login failed"),
    ("p9-web-publishing", "p7-f5", "website down"),
    ("p9-dns-ad", "p7-ad-primary", "DNS resolution failed"),
    ("p9-exchange", "p7-exchange-primary", "mail unavailable"),
    ("p9-vmware", "p7-vcenter", "vCenter degraded"),
    ("p9-firewall-security", "p7-ftd", "traffic blocked"),
    ("p9-storage-backup-switching", "p7-fujitsu-sw1", "storage path errors"),
]


def _evidence(check: dict) -> dict:
    material = f"{check['binding_id']}|{check['check_id']}"
    return {"evidence_id": "p9-fixture-" + hashlib.sha256(material.encode()).hexdigest()[:12], "binding_id": check["binding_id"], "check_id": check["check_id"], "collected_at": datetime.now(timezone.utc).isoformat(), "verification_status": "live_verified", "trust_level": 5, "outcome": "SUCCESS", "summary": "Injected attributable fixture; no live connection.", "observations": {"fixture": True, "signal_count": 1}, "output_sha256_prefix": hashlib.sha256(material.encode()).hexdigest()[:16]}


def run() -> dict:
    engine = P9DiagnosticEngine(BASE_DIR)
    results = []
    for scenario, binding, symptom in CASES:
        initial = engine.plan({"scenario_id": scenario, "binding_id": binding, "symptom": symptom})
        samples = [_evidence(item) for item in initial["candidate_checks"][:2]]
        state = engine.plan({"scenario_id": scenario, "binding_id": binding, "symptom": symptom, "evidence": samples})
        safe = not any(state["safety"].values()) and state["root_cause"] is None and state["metrics"]["handoff_chars"] <= 6000
        results.append({"scenario_id": scenario, "status": state["status"], "evidence": len(state["accepted_evidence"]), "remaining": state["metrics"]["remaining_checks"], "safe": safe})
    passed = sum(item["evidence"] == 2 and item["safe"] for item in results)
    return {"status": "PASS" if passed == len(results) else "FAIL", "passed": passed, "total": len(results), "live_connections": 0, "external_ai_calls": 0, "persistence_attempted": False, "remediation_attempted": False, "results": results}


if __name__ == "__main__":
    report = run()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)
