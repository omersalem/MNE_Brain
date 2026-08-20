#!/usr/bin/env python3
"""
MNE_Brain Release 2 — Milestone 2 Core Flow Validation Suite
Tests Query Router classification, Entity Resolver indexer, Evidence Pack token bounding (<1,500 tokens), and Schema validation.
"""

import sys
import json
import jsonschema
from pathlib import Path

# Add project root to sys.path
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.router.route_query import QueryRouter
from core.entity.build_entity_index import EntityIndexBuilder
from core.evidence.build_evidence_pack import EvidencePackBuilder

def test_milestone_2():
    print("[VALIDATING MILESTONE 2 CORE FLOW ENGINE]")
    errors = []
    passed = 0
    
    # 1. Test Query Router
    router = QueryRouter()
    res_concept = router.classify_query("Explain network topology")
    res_asset = router.classify_query("Show me FortiGate status at 172.23.19.1")
    res_trouble = router.classify_query("Why is 172.23.19.1 unreachable and down?")
    
    if res_concept["route_type"] == "concept":
        print(" [PASS] Query Router concept classification verified")
        passed += 1
    else:
        errors.append(f"Concept classification failed: got {res_concept['route_type']}")
        
    if res_asset["route_type"] == "asset" and res_asset["has_asset"]:
        print(" [PASS] Query Router asset classification verified")
        passed += 1
    else:
        errors.append(f"Asset classification failed: got {res_asset['route_type']}")

    if res_trouble["route_type"] == "troubleshoot":
        print(" [PASS] Query Router troubleshoot classification verified")
        passed += 1
    else:
        errors.append(f"Troubleshoot classification failed: got {res_trouble['route_type']}")

    # 2. Test Entity Resolver
    entity_builder = EntityIndexBuilder(base_dir=base_dir)
    idx = entity_builder.build_index()
    if idx["total_entities"] > 0:
        print(f" [PASS] Entity Resolver index built with {idx['total_entities']} entities")
        passed += 1
    else:
        errors.append("Entity index is empty")

    matches = entity_builder.resolve_entity("What is the status of fortigate firewall?")
    if len(matches) > 0 and matches[0]["entity_id"] == "fw-fortigate-hq-01":
        print(" [PASS] Entity Resolver alias resolution verified ('fortigate')")
        passed += 1
    else:
        errors.append("Entity alias resolution failed for 'fortigate'")

    # 3. Test Evidence Pack Context Engine
    evidence_builder = EvidencePackBuilder(base_dir=base_dir)
    pack = evidence_builder.build_evidence_pack("Check fortigate status", target_entities=matches)
    
    if pack["total_tokens"] <= 1500 and pack["unknowns"]:
        print(f" [PASS] Evidence Pack token bounded and unknowns preserved: actual {pack['total_tokens']} tokens")
        passed += 1
    else:
        errors.append("Evidence pack did not preserve the token budget and explicit unknowns")

    # 4. Validate evidence pack against JSON Schema
    schema_path = base_dir / "00_meta" / "schemas" / "evidence.schema.json"
    with open(schema_path, 'r', encoding='utf-8') as sf:
        schema = json.load(sf)
        
    try:
        jsonschema.validate(instance=pack, schema=schema)
        print(" [PASS] Evidence Pack schema validation passed (evidence.schema.json)")
        passed += 1
    except Exception as e:
        errors.append(f"Evidence schema validation failed: {str(e)}")

    print("\n--- MILESTONE 2 VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for err in errors:
            print(f" - {err}")
        return False
    else:
        print(f"SUCCESS: {passed} Core Flow Engine Components Verified (0 Errors)")
        return True

if __name__ == "__main__":
    success = test_milestone_2()
    sys.exit(0 if success else 1)
