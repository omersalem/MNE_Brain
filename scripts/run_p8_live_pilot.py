#!/usr/bin/env python3
"""Run one exact owner-authorized P8 live read-only troubleshooting scope."""

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.troubleshooting.live_session import P8LiveSession
from scripts.run_p7_authenticated_baseline import AuthenticatedBaselineRunner


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--binding", required=True)
    parser.add_argument("--symptom", default="")
    parser.add_argument("--owner-proceed", action="store_true")
    args = parser.parse_args()
    runner = AuthenticatedBaselineRunner(BASE_DIR)
    session = P8LiveSession(BASE_DIR, runner.run_selected)
    result = session.run({"scenario_id": args.scenario, "binding_id": args.binding, "symptom": args.symptom}, owner_proceed=args.owner_proceed)
    public = {key: value for key, value in result.items() if key not in ("accepted_evidence", "ai_handoff")}
    print(json.dumps(public, indent=2))
    raise SystemExit(0 if result["status"] in ("NOT_RUN", "LIVE_EVIDENCE_ACCEPTED") else 1)
