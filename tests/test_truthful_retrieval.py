#!/usr/bin/env python3
"""Isolated offline checks for entity status and evidence-pack truthfulness."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from jsonschema import validate

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.entity.build_entity_index import EntityIndexBuilder
from core.evidence.build_evidence_pack import EvidencePackBuilder


def _write_note(path: Path, entity_id: str, status: str) -> None:
    evidence_refs = "\nevidence_refs: [\"ev-test-01\"]" if status == "live_verified" else ""
    verification_fields = (
        f"\nverification_target: \"{entity_id}\"\nverification_check_id: \"show-status\"\nverification_outcome: \"success\""
        if status == "live_verified"
        else ""
    )
    last_verified = (
        datetime.now(timezone.utc).isoformat() if status == "live_verified" else "null"
    )
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
last_verified: {last_verified}
freshness_ttl_hours: 720{evidence_refs}
{verification_fields}
---

# {entity_id}
''',
        encoding="utf-8",
    )


def test_unverified_entities_are_not_evidence() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        knowledge = root / "knowledge" / "network"
        knowledge.mkdir(parents=True)
        _write_note(knowledge / "documented.md", "documented-device", "documented")
        _write_note(knowledge / "unverified.md", "unverified-device", "unverified")
        _write_note(knowledge / "live.md", "live-device", "live_verified")

        EntityIndexBuilder._index_cache.clear()
        entities = EntityIndexBuilder(base_dir=root).build_index()
        assert entities["total_entities"] == 3
        assert not (root / "00_meta" / "indices" / "entity-index.json").exists()

        builder = EvidencePackBuilder(base_dir=root)
        pack = builder.build_evidence_pack(
            "Compare test devices", target_entities=entities["entities"]
        )
        assert len(pack["evidence_blocks"]) == 2
        documented = next(block for block in pack["evidence_blocks"] if block["entity_id"] == "documented-device")
        live = next(block for block in pack["evidence_blocks"] if block["entity_id"] == "live-device")
        assert documented["evidence_status"] == "documented"
        assert documented["trust_level"] == 3
        assert live["evidence_status"] == "live_verified"
        assert live["trust_level"] == 5
        assert live["evidence_refs"] == ["ev-test-01"]
        assert isinstance(live["observed_at"], str)
        assert any("unverified-device is unverified" in item for item in pack["unknowns"])
        assert not (root / "00_meta" / "indices" / "evidence-pack.json").exists()

        schema = json.loads(
            (base_dir / "00_meta" / "schemas" / "evidence.schema.json").read_text(encoding="utf-8")
        )
        validate(pack, schema)


if __name__ == "__main__":
    test_unverified_entities_are_not_evidence()
    print("Truthful retrieval test passed.")
