import sys
import os
import json
import yaml
import datetime

VAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, VAULT_ROOT)

from scripts.route_query import route_query
from scripts.build_entity_index import resolve_entity
from scripts.build_evidence_pack import EvidencePackBuilder

SCENARIOS_PATH = os.path.join(VAULT_ROOT, "benchmarks", "scenarios.yaml")
REPORT_OUTPUT_DIR = os.path.join(VAULT_ROOT, "operations", "quality")

def run_benchmarks():
    today_str = datetime.date.today().isoformat()
    os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
    report_path = os.path.join(REPORT_OUTPUT_DIR, f"benchmark-report-{today_str}.md")

    if not os.path.exists(SCENARIOS_PATH):
        print(f"Scenarios file missing: {SCENARIOS_PATH}")
        return 1

    with open(SCENARIOS_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    scenarios = data.get("scenarios", [])
    passed = 0
    failed = 0
    results = []

    builder = EvidencePackBuilder()

    for scen in scenarios:
        sid = scen["id"]
        sname = scen["name"]
        q = scen["question"]
        exp_route = scen["expected_route"]

        # Step 1: Routing Check
        r_out = route_query(q)
        route_ok = (r_out["route"] == exp_route)

        # Step 2: Entity Resolution Check
        if scen.get("target_entity"):
            ent_res = resolve_entity(scen["target_entity"])
            ent_ok = (ent_res["status"] in ["exact_match", "ambiguous", "unknown"])
        else:
            ent_ok = True

        # Step 3: Evidence Pack Check
        pack = builder.build_pack(q, scen.get("target_entity"))
        pack_ok = bool(pack and "query_route" in pack)

        # Step 4: Remediation Gate Check
        if exp_route == "remediation":
            gate_ok = r_out.get("remediation_gate_required", False)
        else:
            gate_ok = True

        scen_passed = (route_ok and ent_ok and pack_ok and gate_ok)
        if scen_passed:
            passed += 1
            status_symbol = "✅ PASS"
        else:
            failed += 1
            status_symbol = "❌ FAIL"

        results.append({
            "id": sid,
            "name": sname,
            "status": status_symbol,
            "route_actual": r_out["route"],
            "route_expected": exp_route,
            "gate_enforced": gate_ok
        })

    # Generate Markdown report
    lines = [
        f"# Benchmark Execution Report — {today_str}",
        "",
        f"- **Total Benchmark Scenarios:** {len(scenarios)}",
        f"- **Passed:** {passed}",
        f"- **Failed:** {failed}",
        f"- **Pass Rate:** {(passed / len(scenarios)) * 100:.1f}%",
        "",
        "## 📊 Scenario Results Table",
        "| ID | Scenario | Status | Route Actual | Route Expected | Remediation Gate |",
        "|---|---|---|---|---|---|"
    ]
    for r in results:
        lines.append(f"| `{r['id']}` | {r['name']} | {r['status']} | `{r['route_actual']}` | `{r['route_expected']}` | {'Yes' if r['gate_enforced'] else 'N/A'} |")

    with open(report_path, "w", encoding="utf-8") as rf:
        rf.write("\n".join(lines))

    print(f"[BENCHMARK] Executed {len(scenarios)} scenarios. Passed: {passed}, Failed: {failed}.")
    print(f"[BENCHMARK] Written report to {report_path}")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(run_benchmarks())
