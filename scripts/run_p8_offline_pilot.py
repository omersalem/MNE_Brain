#!/usr/bin/env python3
"""Run all P8 scenario families without connecting to infrastructure."""

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.troubleshooting.engine import P8TroubleshootingEngine


CASES = [
    ("p8-branch-outage", "p7-fortigate-nablus", "branch down"),
    ("p8-vpn-access", "p7-fortigate-edge", "VPN login failed"),
    ("p8-web-publishing", "p7-f5", "website down"),
    ("p8-dns-ad", "p7-ad-primary", "DNS name resolution failed"),
    ("p8-exchange", "p7-exchange-primary", "email unavailable"),
    ("p8-vmware", "p7-vcenter", "vCenter unavailable"),
    ("p8-firewall-security", "p7-ftd", "traffic blocked"),
    ("p8-storage-backup-switching", "p7-fujitsu-sw1", "storage unavailable"),
]


def run() -> dict:
    engine = P8TroubleshootingEngine(BASE_DIR)
    results = []
    for scenario, binding, symptom in CASES:
        result = engine.plan({"scenario_id": scenario, "binding_id": binding, "symptom": symptom})
        results.append({"scenario_id": scenario, "binding_id": binding, "status": result["status"], "checks": len(result["planned_checks"]), "handoff_chars": result["metrics"]["handoff_chars"], "safe": not any(result["safety"].values())})
    passed = sum(item["status"] == "EVIDENCE_REQUIRED" and item["safe"] and 1 <= item["checks"] <= 3 for item in results)
    return {"status": "PASS" if passed == len(results) else "FAIL", "passed": passed, "total": len(results), "live_connections": 0, "persistence_attempted": False, "remediation_attempted": False, "results": results}


if __name__ == "__main__":
    report = run()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)
