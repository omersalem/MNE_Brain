#!/usr/bin/env python3
"""Run one exact owner-authorized P9 deep read-only diagnostic session."""

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.troubleshooting.p9_collector import P9LiveCollector
from core.troubleshooting.p9_live_session import P9LiveSession


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--binding", required=True)
    parser.add_argument("--symptom", default="")
    parser.add_argument("--owner-proceed", action="store_true")
    args = parser.parse_args()
    collector = P9LiveCollector(BASE_DIR)
    session = P9LiveSession(BASE_DIR, collector.collect)
    result = session.run({"scenario_id": args.scenario, "binding_id": args.binding, "symptom": args.symptom}, owner_proceed=args.owner_proceed)
    public = {key: value for key, value in result.items() if key != "ai_handoff"}
    print(json.dumps(public, indent=2))
    raise SystemExit(0 if result["status"] in ("NOT_RUN", "MORE_EVIDENCE_AVAILABLE", "READY_FOR_AI_REASONING", "STOP_EARLY_EVIDENCE_BOUND") else 1)
