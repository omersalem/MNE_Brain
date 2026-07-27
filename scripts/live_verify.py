import sys
import os
import argparse
import json

VAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, VAULT_ROOT)

from scripts.adapters.fortigate_read import execute_fortigate_read

def main():
    parser = argparse.ArgumentParser(description="Live Read-Only Verification Runner for MNE Brain")
    parser.add_argument("--device", default="fw-fortigate-hq-01", help="Target device ID")
    parser.add_argument("--check", default="get_system_status", help="Approved check ID")
    parser.add_argument("--mock", action="store_true", default=True, help="Use mock adapter response")
    args = parser.parse_args()

    print(f"=== Executing Live Verification: [{args.device}] -> Check: [{args.check}] ===")
    result = execute_fortigate_read(target_entity=args.device, check_id=args.check, use_mock=args.mock)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
