#!/usr/bin/env python3
"""Offline validation for non-destructive, attributable knowledge lifecycle work."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.lifecycle.lifecycle_engine import KnowledgeLifecycleEngine


def _write_note(path: Path, entity_id: str, status: str, facts: dict[str, str]) -> None:
    live_fields = "" if status != "live_verified" else """
evidence_refs: ["ev-canonical-01"]
verification_target: "test-edge-01"
verification_check_id: "show-interface"
verification_outcome: "success"
"""
    timestamp = datetime.now(timezone.utc).isoformat() if status == "live_verified" else "null"
    facts_yaml = "\n".join(f"  {key}: \"{value}\"" for key, value in facts.items())
    path.write_text(
        f'''---
id: "{entity_id}"
name: "{entity_id}"
category: "network"
aliases: ["{entity_id}-alias"]
owner: "Test Team"
related_entities: []
knowledge_status: "{status}"
source: "isolated-test-fixture"
last_verified: {timestamp}
freshness_ttl_hours: 720
{live_fields}facts:
{facts_yaml}
---

# {entity_id}
''',
        encoding="utf-8",
    )


def _live_evidence(entity_id: str, facts: dict[str, str]) -> dict[str, object]:
    return {
        "entity_id": entity_id,
        "source_file": "operations/verification/test-edge-01.json",
        "source": "owner-authorized read-only test fixture",
        "evidence_status": "live_verified",
        "trust_level": 5,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "evidence_refs": ["ev-live-01"],
        "verification_target": "test-edge-01",
        "verification_check_id": "show-interface",
        "verification_outcome": "success",
        "observed_facts": facts,
    }


def test_milestone_6() -> bool:
    print("[VALIDATING MILESTONE 6 KNOWLEDGE LIFECYCLE ENGINE]")
    errors: list[str] = []
    passed = 0

    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        knowledge = root / "knowledge" / "network"
        knowledge.mkdir(parents=True)
        unverified_note = knowledge / "unverified.md"
        accepted_note = knowledge / "accepted.md"
        _write_note(unverified_note, "test-unverified-01", "unverified", {"port2.link_state": "down"})
        _write_note(accepted_note, "test-edge-01", "live_verified", {"port2.link_state": "down"})
        lifecycle = KnowledgeLifecycleEngine(base_dir=root)

        unverified = lifecycle.detect_knowledge_drift(
            "test-unverified-01", "knowledge/network/unverified.md", _live_evidence("test-unverified-01", {"port2.link_state": "up"})
        )
        raw_telemetry = lifecycle.detect_knowledge_drift(
            "test-edge-01", "knowledge/network/accepted.md", "port2: link up"
        )
        if (
            unverified["status"] == "CANONICAL_NOT_ACCEPTED"
            and raw_telemetry["status"] == "INSUFFICIENT_LIVE_EVIDENCE"
            and not (root / "operations").exists()
        ):
            print(" [PASS] Unverified canonical notes and raw telemetry cannot create lifecycle state")
            passed += 1
        else:
            errors.append(f"Evidence gating failed: unverified={unverified}, raw={raw_telemetry}")

        original_canonical = accepted_note.read_text(encoding="utf-8")
        no_drift = lifecycle.detect_knowledge_drift(
            "test-edge-01", "knowledge/network/accepted.md", _live_evidence("test-edge-01", {"port2.link_state": "down"})
        )
        in_memory_drift = lifecycle.detect_knowledge_drift(
            "test-edge-01", "knowledge/network/accepted.md", _live_evidence("test-edge-01", {"port2.link_state": "up"})
        )
        if (
            no_drift["status"] == "NO_DRIFT"
            and in_memory_drift["status"] == "DRIFT_DETECTED"
            and accepted_note.read_text(encoding="utf-8") == original_canonical
            and not (root / "operations").exists()
        ):
            print(" [PASS] Comparable facts detect drift in memory without canonical or operations writes")
            passed += 1
        else:
            errors.append(f"In-memory drift handling failed: no_drift={no_drift}, drift={in_memory_drift}")

        persisted_drift = lifecycle.detect_knowledge_drift(
            "test-edge-01",
            "knowledge/network/accepted.md",
            _live_evidence("test-edge-01", {"port2.link_state": "up"}),
            persist=True,
        )
        review_queue_path = root / "operations" / "discovery" / "review_queue.json"
        history_path = root / "operations" / "discovery" / "verification_history.json"
        queue = json.loads(review_queue_path.read_text(encoding="utf-8")) if review_queue_path.exists() else []
        history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else {}
        if (
            persisted_drift["persistence"] == "HISTORY_RECORDED_AND_PROPOSAL_STAGED"
            and len(queue) == 1
            and queue[0]["status"] == "PENDING_OWNER_REVIEW"
            and queue[0]["auto_overwrite_allowed"] is False
            and queue[0]["evidence_refs"] == ["ev-live-01"]
            and len(history.get("events", [])) == 1
        ):
            print(" [PASS] Explicit persistence creates a sole-owner review proposal and history event")
            passed += 1
        else:
            errors.append(f"Review staging failed: report={persisted_drift}, queue={queue}, history={history}")

        duplicate = lifecycle.detect_knowledge_drift(
            "test-edge-01",
            "knowledge/network/accepted.md",
            _live_evidence("test-edge-01", {"port2.link_state": "up"}),
            persist=True,
        )
        owner_review = lifecycle.promote_to_canonical(
            queue[0]["proposal_id"], explicit_owner_instruction=True
        )
        updated_queue = json.loads(review_queue_path.read_text(encoding="utf-8"))
        if (
            duplicate["persistence"] == "HISTORY_RECORDED_AND_EXISTING_PROPOSAL_RETAINED"
            and len(updated_queue) == 1
            and owner_review["owner_reviewed_for_manual_promotion"] is True
            and owner_review["promoted"] is False
            and owner_review["reviewed_by"] == "MNE-BRAIN-OWNER"
            and updated_queue[0]["status"] == "OWNER_REVIEWED_FOR_MANUAL_PROMOTION"
            and accepted_note.read_text(encoding="utf-8") == original_canonical
        ):
            print(" [PASS] Proposals deduplicate and sole-owner review never edits canonical knowledge")
            passed += 1
        else:
            errors.append(f"Owner-review safety failed: duplicate={duplicate}, review={owner_review}")

    print("\n--- MILESTONE 6 VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for error in errors:
            print(f" - {error}")
        return False
    print(f"SUCCESS: {passed} Knowledge Lifecycle Components Verified (0 Errors)")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_milestone_6() else 1)
