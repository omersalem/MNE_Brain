#!/usr/bin/env python3
"""Run bounded P7 reachability for all exact entities; retain nothing."""

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.transports.preflight import LivePreflightValidator


def run(*, owner_proceed: bool, timeout_seconds: float = 2.0) -> dict:
    return LivePreflightValidator(base_dir=BASE_DIR).validate_all(
        owner_proceed=owner_proceed, timeout_seconds=timeout_seconds
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-proceed", action="store_true", help="Use only after the sole owner explicitly says proceed.")
    parser.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args()
    result = run(owner_proceed=args.owner_proceed, timeout_seconds=args.timeout)
    # Print only aggregate state: target addresses and raw handshakes are never emitted.
    print(json.dumps({
        "status": result["status"],
        "total_entities": result["total_entities"],
        "status_counts": result["status_counts"],
        "raw_output_included": result["raw_output_included"],
        "credentials_returned": result["credentials_returned"],
        "persistence_attempted": result["persistence_attempted"],
        "notifications_sent": result["notifications_sent"],
        "remediation_attempted": result["remediation_attempted"],
    }, indent=2))
    raise SystemExit(0 if result["status"] == "COMPLETE" else 1)
