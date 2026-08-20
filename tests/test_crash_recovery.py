#!/usr/bin/env python3
"""Stateless recovery tests that never delete or overwrite project artifacts."""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.entity.build_entity_index import EntityIndexBuilder
from core.evidence.build_evidence_pack import EvidencePackBuilder


def test_crash_recovery() -> bool:
    print("[RUNNING ISOLATED STATELESS RECOVERY SUITE]")
    errors: list[str] = []
    passed = 0

    with TemporaryDirectory() as temporary_directory:
        isolated_root = Path(temporary_directory)
        knowledge_dir = isolated_root / "knowledge" / "network"
        indices_dir = isolated_root / "00_meta" / "indices"
        knowledge_dir.mkdir(parents=True)
        indices_dir.mkdir(parents=True)
        note = knowledge_dir / "test-edge-canonical.md"
        note.write_text(
            """---
id: test-edge-01
name: Test Edge Device
category: network
aliases: [test-edge]
hostname: test-edge-01
ip: 192.0.2.44
owner: Offline Test Team
related_entities: []
knowledge_status: unverified
source: isolated-recovery-fixture
last_verified: null
freshness_ttl_hours: 24
---
# Test Edge Device
""",
            encoding="utf-8",
        )
        entity_cache = indices_dir / "entity-index.json"
        evidence_cache = indices_dir / "evidence-pack.json"
        entity_cache.write_text("{corrupted-entity-cache", encoding="utf-8")
        evidence_cache.write_text("{corrupted-evidence-cache", encoding="utf-8")

        builder = EntityIndexBuilder(base_dir=isolated_root)
        index = builder.build_index(persist=False)
        resolved = builder.resolve_entity("192.0.2.44")
        caches_unchanged_after_index = (
            entity_cache.read_text(encoding="utf-8") == "{corrupted-entity-cache"
            and evidence_cache.read_text(encoding="utf-8") == "{corrupted-evidence-cache"
        )
        if index["total_entities"] == 1 and resolved[0]["entity_id"] == "test-edge-01" and caches_unchanged_after_index:
            print(" [PASS] In-memory entity rebuild ignores and preserves corrupted cache artifacts")
            passed += 1
        else:
            errors.append(f"Entity stateless recovery failed: index={index}, resolved={resolved}")

        pack = EvidencePackBuilder(base_dir=isolated_root).build_evidence_pack(
            "Check test edge status", resolved, persist=False
        )
        caches_unchanged_after_evidence = (
            entity_cache.read_text(encoding="utf-8") == "{corrupted-entity-cache"
            and evidence_cache.read_text(encoding="utf-8") == "{corrupted-evidence-cache"
        )
        if pack["evidence_blocks"] == [] and pack["unknowns"] and caches_unchanged_after_evidence:
            print(" [PASS] Evidence rebuild remains truthful and does not rewrite corrupted cache artifacts")
            passed += 1
        else:
            errors.append(f"Evidence stateless recovery failed: {pack}")

    print("\n--- ISOLATED STATELESS RECOVERY SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for error in errors:
            print(f" - {error}")
        return False
    print(f"SUCCESS: {passed} Recovery Scenarios Passed (0 Errors)")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_crash_recovery() else 1)
