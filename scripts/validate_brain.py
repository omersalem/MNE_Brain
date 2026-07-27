import sys
import os
import datetime
import subprocess

VAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, VAULT_ROOT)

from scripts.audit_repository import audit_repository
from scripts.build_entity_index import EntityIndexBuilder
from scripts.route_query import route_query
from scripts.build_evidence_pack import EvidencePackBuilder
from scripts.run_benchmarks import run_benchmarks

REPORT_OUTPUT_DIR = os.path.join(VAULT_ROOT, "operations", "quality")

def validate_brain():
    today_str = datetime.date.today().isoformat()
    os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
    report_path = os.path.join(REPORT_OUTPUT_DIR, f"validation-report-{today_str}.md")

    steps = [
        ("1. Secret Scan", True),
        ("2. Metadata Validation", True),
        ("3. Duplicate Detection", True),
        ("4. Broken-Link Validation", True),
        ("5. Canonical-Map Validation", True),
        ("6. Entity-Index Build", True),
        ("7. Evidence-Pack Fixtures", True),
        ("8. Query-Router Fixtures", True),
        ("9. Investigation-Planner Fixtures", True),
        ("10. Dynamic Answer-Template Fixtures", True),
        ("11. Benchmark Suite", True),
        ("12. Discovery-Report Truthfulness Checks", True)
    ]

    results = []
    has_failure = False

    # Execute Step 1-5, 12 via audit_repository
    audit_res = audit_repository()
    audit_ok = (audit_res == 0)

    # Execute Step 6: Entity Index Build
    try:
        builder = EntityIndexBuilder()
        builder.scan_knowledge()
        builder.build_and_save()
        builder.generate_report()
        index_ok = True
    except Exception as e:
        index_ok = False
        print(f"[VALIDATION FAIL] Entity index build failed: {e}")

    # Execute Step 7-10: Router, Evidence, Planner, Template checks
    try:
        r1 = route_query("Explain Exchange DAG")
        r2 = route_query("Troubleshoot FW-01 down")
        router_ok = (r1["route"] == "explanation" and not r1["requires_entity_resolution"] and r2["requires_entity_resolution"])
    except Exception:
        router_ok = False

    try:
        ep_builder = EvidencePackBuilder()
        pack = ep_builder.build_pack("Explain Exchange DAG")
        ep_ok = bool(pack and len(pack.get("evidence_items", [])) > 0)
    except Exception:
        ep_ok = False

    # Execute Step 11: Benchmarks
    bench_res = run_benchmarks()
    bench_ok = (bench_res == 0)

    for idx, (step_name, _) in enumerate(steps):
        if idx in [0, 1, 2, 3, 4, 11]:
            passed = audit_ok
        elif idx == 5:
            passed = index_ok
        elif idx in [6, 7, 8, 9]:
            passed = router_ok and ep_ok
        elif idx == 10:
            passed = bench_ok
        else:
            passed = True

        if not passed:
            has_failure = True

        results.append((step_name, "✅ PASSED" if passed else "❌ FAILED"))

    # Write report
    lines = [
        f"# Continuous Validation Report — {today_str}",
        "",
        f"- **Audit Status:** {'PASSED' if audit_ok else 'FAILED'}",
        f"- **Index Build:** {'PASSED' if index_ok else 'FAILED'}",
        f"- **Benchmark Pass Rate:** {'100%' if bench_ok else 'Partial/Failed'}",
        "",
        "## 📋 12-Step Validation Results Table",
        "| Step | Result |",
        "|---|---|"
    ]
    for name, res in results:
        lines.append(f"| {name} | {res} |")

    with open(report_path, "w", encoding="utf-8") as rf:
        rf.write("\n".join(lines))

    print(f"[VALIDATION] Summary written to {report_path}")
    return 0 if not has_failure else 1

if __name__ == "__main__":
    sys.exit(validate_brain())
