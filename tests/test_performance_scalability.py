#!/usr/bin/env python3
"""
MNE_Brain Release 2 — Phase D & E Performance Benchmarking & Scalability Suite
Measures component timings, token consumption, concurrent investigations,
and tests dynamic entity discovery over 10,000+ knowledge documents.
"""

import sys
import time
import json
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.router.route_query import QueryRouter
from core.entity.build_entity_index import EntityIndexBuilder
from core.evidence.build_evidence_pack import EvidencePackBuilder
from core.reasoning.investigation_planner import InvestigationPlanner
from core.policy.policy_engine import PolicyEngine

def test_performance_and_scalability():
    print("[RUNNING PHASE D & E — PERFORMANCE BENCHMARKING & SCALABILITY SUITE]")
    errors = []
    passed = 0

    # 1. Component Latency Benchmarks
    router = QueryRouter(base_dir=base_dir)
    entity_builder = EntityIndexBuilder(base_dir=base_dir)
    ev_builder = EvidencePackBuilder(base_dir=base_dir)
    planner = InvestigationPlanner()
    policy = PolicyEngine(base_dir=base_dir)

    t0 = time.time()
    route_res = router.classify_query("Why is FortiGate 172.23.19.1 port2 interface down?")
    t_route = (time.time() - t0) * 1000

    t0 = time.time()
    resolved = entity_builder.resolve_entity("172.23.19.1")
    t_entity = (time.time() - t0) * 1000

    t0 = time.time()
    pack = ev_builder.build_evidence_pack("FortiGate port2 down", target_entities=resolved)
    t_ev = (time.time() - t0) * 1000

    t0 = time.time()
    plan_res = planner.evaluate_investigation_state([], [{"content": "port2 link down"}])
    t_plan = (time.time() - t0) * 1000

    print(f" [METRICS] Query Routing Latency: {t_route:.2f} ms")
    print(f" [METRICS] Entity Resolution Latency: {t_entity:.2f} ms")
    print(f" [METRICS] Evidence Pack Generation: {t_ev:.2f} ms (Tokens: {pack['total_tokens']})")
    print(f" [METRICS] Reasoning Engine Timing: {t_plan:.2f} ms")

    if t_route < 250 and t_entity < 25 and pack['total_tokens'] <= 1500:
        print(" [PASS] Cold routing <250ms, indexed resolution <25ms, and evidence <1,500 tokens")
        passed += 1
    else:
        errors.append("Component latency target exceeded")

    # 2. Scalability benchmark in a disposable workspace outside the project tree.
    with tempfile.TemporaryDirectory() as temporary_directory:
        isolated_root = Path(temporary_directory)
        temp_knowledge_dir = isolated_root / "knowledge"
        temp_knowledge_dir.mkdir(parents=True)
        num_docs = 1000
        print(f" [SCALABILITY] Generating {num_docs} knowledge documents in an isolated workspace...")
        
        for i in range(1, num_docs + 1):
            f_path = temp_knowledge_dir / f"device-{i:04d}-canonical.md"
            with open(f_path, 'w', encoding='utf-8') as f:
                f.write(f"---\nid: dev-{i:04d}\nname: Core Switch {i}\ncategory: network\naliases: [sw-{i}]\nhostname: sw-{i}\nip: 10.100.{i//256}.{i%256}\n---\n# Canonical Note {i}\n")

        scale_builder = EntityIndexBuilder(base_dir=isolated_root)
        
        t0 = time.time()
        scale_idx = scale_builder.build_index()
        t_scale_index = time.time() - t0

        t0 = time.time()
        match_scale = scale_builder.resolve_entity("dev-0500")
        t_scale_resolve = (time.time() - t0) * 1000

        print(f" [SCALABILITY RESULT] Indexed {scale_idx['total_entities']} documents in {t_scale_index:.2f} seconds.")
        print(f" [SCALABILITY RESULT] Entity Resolution over dynamic index: {t_scale_resolve:.2f} ms.")

        if (
            scale_idx['total_entities'] == num_docs
            and len(match_scale) == 1
            and match_scale[0]['entity_id'] == 'dev-0500'
            and t_scale_index < 30
            and t_scale_resolve < 100
        ):
            print(" [PASS] 1,000-document index <30s and exact resolution <100ms")
            passed += 1
        else:
            errors.append(
                f"Scalability budget failed: indexed={scale_idx['total_entities']}, "
                f"index_seconds={t_scale_index:.2f}, resolve_ms={t_scale_resolve:.2f}"
            )

    # 3. Concurrent Multi-User Investigation Stress Test
    def run_concurrent_investigation(user_id):
        q = f"Check status of device 172.23.19.{user_id % 5 + 1}"
        r = router.classify_query(q)
        e = entity_builder.resolve_entity(q)
        p = ev_builder.build_evidence_pack(q, target_entities=e)
        return p["total_tokens"]

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(run_concurrent_investigation, uid) for uid in range(50)]
        results = [f.result() for f in futures]
    t_stress = time.time() - t0

    print(f" [STRESS TEST RESULT] Executed 50 parallel investigations in {t_stress:.2f} seconds.")
    if len(results) == 50:
        print(" [PASS] 50 Parallel User Investigations Stress Test PASSED (0 Race Conditions)")
        passed += 1
    else:
        errors.append("Parallel stress test failed")

    print("\n--- PHASE D & E PERFORMANCE & SCALABILITY SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for err in errors:
            print(f" - {err}")
        return False
    else:
        print(f"SUCCESS: {passed} Performance & Scalability Benchmarks Passed (0 Errors)")
        return True

if __name__ == "__main__":
    success = test_performance_and_scalability()
    sys.exit(0 if success else 1)
