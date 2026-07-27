import sys
import os
import argparse
import datetime

VAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    parser = argparse.ArgumentParser(description="AI-Native Infrastructure Discovery Runner")
    parser.add_argument("--task", required=True, choices=["network", "virtualization", "identity", "messaging", "linux", "storage"], help="Target domain task")
    args = parser.parse_args()

    start_time = datetime.datetime.now()
    today_str = datetime.date.today().isoformat()

    print(f"=== Starting AI-Native Discovery Task: [{args.task.upper()}] at {start_time.isoformat()} ===")

    task_profile_map = {
        "network": ["fortigate.yaml", "cisco.yaml", "f5.yaml"],
        "virtualization": ["vmware.yaml"],
        "identity": ["identity.yaml"],
        "messaging": ["exchange.yaml"],
        "linux": ["linux.yaml"],
        "storage": ["storage.yaml"]
    }

    profiles_used = task_profile_map.get(args.task, [])
    report_dir = os.path.join(VAULT_ROOT, "operations", "discovery")
    evidence_dir = os.path.join(VAULT_ROOT, "operations", "evidence")
    os.makedirs(report_dir, exist_ok=True)
    report_filename = f"{today_str}-{args.task}-discovery.md"
    report_path = os.path.join(report_dir, report_filename)

    # Truthful status evaluation: check if evidence adapter emitted live evidence
    has_live_evidence = False
    if os.path.exists(evidence_dir):
        evidence_files = [f for f in os.listdir(evidence_dir) if f.startswith(f"{args.task}-") and f.endswith(".json")]
        if evidence_files:
            has_live_evidence = True

    status_str = "live_verified" if has_live_evidence else "not_run"
    trust_tier_str = "Tier 5 (Live Read-Only Evidence)" if has_live_evidence else "Tier 0 (No Live Execution)"

    report_content = f"""# Infrastructure Discovery Report: {args.task.upper()}

- **Execution Date:** {start_time.isoformat()}
- **Orchestration Model:** Task ➔ Discovery Profile ➔ Adapter ➔ Evidence Pack
- **Profiles Requested:** {', '.join(profiles_used)}
- **Status:** {status_str}

## 📋 Discovery Profiles Configured
{chr(10).join(f"- `profiles/{p}`" for p in profiles_used)}

## 🔬 Telemetry & Source Attribution
- Trust Tier: {trust_tier_str}
- Live Evidence Attached: {'Yes' if has_live_evidence else 'No (Dry Run / Static Policy)'}

## 📁 Artifacts
- Discovery Report: `operations/discovery/{report_filename}`
"""

    with open(report_path, "w", encoding="utf-8") as rf:
        rf.write(report_content)

    print(f"[DISCOVERY] Written Report: {report_path} with status: {status_str}")
    print(f"=== Discovery Task [{args.task.upper()}] Completed ===")

if __name__ == "__main__":
    main()
