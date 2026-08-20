#!/usr/bin/env python3
"""Eleven deterministic, offline Ministry troubleshooting evidence-flow benchmarks."""

import sys
import time
from pathlib import Path
from typing import Any

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.entity.build_entity_index import EntityIndexBuilder
from core.evidence.build_evidence_pack import EvidencePackBuilder
from core.llm.llm_adapter import LLMAdapter
from core.policy.policy_engine import PolicyEngine
from core.reasoning.investigation_planner import InvestigationPlanner
from core.router.route_query import QueryRouter


BENCHMARK_SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "id": "bm-01",
        "name": "HQ firewall reachability",
        "query": "Why is fw-fortigate-hq-01 unreachable?",
        "expected_route": "troubleshoot",
        "expected_resolution": "exact",
        "expected_entities": ["fw-fortigate-hq-01"],
    },
    {
        "id": "bm-02",
        "name": "Core switch status",
        "query": "Check status of sw-cisco-core-01",
        "expected_route": "asset",
        "expected_resolution": "exact",
        "expected_entities": ["sw-cisco-core-01"],
    },
    {
        "id": "bm-03",
        "name": "Virtualization service lookup",
        "query": "Check health of vc-vmware-hq-01",
        "expected_route": "asset",
        "expected_resolution": "exact",
        "expected_entities": ["vc-vmware-hq-01"],
    },
    {
        "id": "bm-04",
        "name": "Active Directory DNS lookup",
        "query": "Check status of dc-mne-ad-01 DNS service",
        "expected_route": "asset",
        "expected_resolution": "exact",
        "expected_entities": ["dc-mne-ad-01"],
    },
    {
        "id": "bm-05",
        "name": "Exchange mail service lookup",
        "query": "Check health of ex-windows-mail-01",
        "expected_route": "asset",
        "expected_resolution": "exact",
        "expected_entities": ["ex-windows-mail-01"],
    },
    {
        "id": "bm-06",
        "name": "Storage capacity lookup",
        "query": "Check status of san-fujitsu-01",
        "expected_route": "asset",
        "expected_resolution": "exact",
        "expected_entities": ["san-fujitsu-01"],
    },
    {
        "id": "bm-07",
        "name": "Backup failure triage",
        "query": "Why did backup-veeam-hq-01 backup fail?",
        "expected_route": "troubleshoot",
        "expected_resolution": "exact",
        "expected_entities": ["backup-veeam-hq-01"],
    },
    {
        "id": "bm-08",
        "name": "F5 service outage triage",
        "query": "Why is waf-f5-bigip-01 service down?",
        "expected_route": "troubleshoot",
        "expected_resolution": "exact",
        "expected_entities": ["waf-f5-bigip-01"],
    },
    {
        "id": "bm-09",
        "name": "Jenin branch firewall triage",
        "query": "Why is fw-fortigate-jenin-01 unreachable?",
        "expected_route": "troubleshoot",
        "expected_resolution": "exact",
        "expected_entities": ["fw-fortigate-jenin-01"],
    },
    {
        "id": "bm-10",
        "name": "Architecture concept question",
        "query": "Explain network segmentation principles",
        "expected_route": "concept",
        "expected_resolution": "not_required",
        "expected_entities": [],
    },
    {
        "id": "bm-11",
        "name": "Unknown incident clarification",
        "query": "Unknown mystery outage",
        "expected_route": "troubleshoot",
        "expected_resolution": "unknown",
        "expected_entities": [],
    },
)


def evaluate_scenario(
    scenario: dict[str, Any],
    *,
    router: QueryRouter,
    entity_builder: EntityIndexBuilder,
    evidence_builder: EvidencePackBuilder,
    planner: InvestigationPlanner,
    policy: PolicyEngine,
    llm: LLMAdapter,
) -> dict[str, Any]:
    """Run one scenario through read-only components without live verification."""
    started = time.perf_counter()
    query = scenario["query"]
    route = router.classify_query(query)
    entities = entity_builder.resolve_entity(query) if route["requires_entity_resolution"] else []
    evidence = evidence_builder.build_evidence_pack(query, entities, persist=False)
    reasoning = planner.evaluate_investigation_state([], evidence["evidence_blocks"])
    policy_result = policy.evaluate_verification_necessity(
        route["route_type"], has_current_live_evidence=False
    )
    answer = llm.generate_response(query, evidence)
    duration_ms = round((time.perf_counter() - started) * 1000, 3)

    expected_policy = "NOT_REQUIRED" if route["route_type"] == "concept" else "DISABLED_BY_POLICY"
    checks = {
        "route": route["route_type"] == scenario["expected_route"],
        "resolution": route["resolution_status"] == scenario["expected_resolution"],
        "entities": route["resolved_entity_ids"] == scenario["expected_entities"],
        "token_budget": evidence["total_tokens"] <= evidence["max_token_budget"] == 1500,
        "truth_boundary": evidence["evidence_blocks"] == [] and bool(evidence["unknowns"]),
        "reasoning_boundary": (
            reasoning["reasoning_status"] == "PENDING_EVIDENCE"
            and reasoning["conclusive_root_cause"] is None
            and reasoning["stop_early_triggered"] is False
        ),
        "policy_boundary": policy_result["execution_status"] == expected_policy,
        "answer_boundary": (
            answer["evidence_status"] == "INSUFFICIENT_EVIDENCE"
            and answer["trust_level"] == 0
            and answer["external_call_attempted"] is False
        ),
        "latency_budget": duration_ms <= 500.0,
    }
    return {
        "id": scenario["id"],
        "name": scenario["name"],
        "passed": all(checks.values()),
        "duration_ms": duration_ms,
        "route": route["route_type"],
        "resolution": route["resolution_status"],
        "evidence_tokens": evidence["total_tokens"],
        "answer_status": answer["evidence_status"],
        "checks": checks,
    }


def run_benchmarks() -> dict[str, Any]:
    print("=" * 66)
    print(" MNE_Brain Release 2 - Offline Evidence-Flow Benchmarks")
    print("=" * 66)
    router = QueryRouter(base_dir=base_dir)
    entity_builder = EntityIndexBuilder(base_dir=base_dir)
    evidence_builder = EvidencePackBuilder(base_dir=base_dir)
    planner = InvestigationPlanner()
    policy = PolicyEngine(base_dir=base_dir)
    llm = LLMAdapter(provider="local_fallback", base_dir=base_dir)

    results = [
        evaluate_scenario(
            scenario,
            router=router,
            entity_builder=entity_builder,
            evidence_builder=evidence_builder,
            planner=planner,
            policy=policy,
            llm=llm,
        )
        for scenario in BENCHMARK_SCENARIOS
    ]
    for result in results:
        outcome = "PASS" if result["passed"] else "FAIL"
        failed_checks = [name for name, passed in result["checks"].items() if not passed]
        detail = "all boundaries" if not failed_checks else "failed=" + ",".join(failed_checks)
        print(
            f"[{outcome}] {result['id']} {result['name']} | route={result['route']} "
            f"resolution={result['resolution']} evidence={result['evidence_tokens']} tokens "
            f"answer={result['answer_status']} latency={result['duration_ms']:.3f} ms | {detail}"
        )

    passed_count = sum(result["passed"] for result in results)
    report = {
        "success": passed_count == len(results) == 11,
        "passed": passed_count,
        "total": len(results),
        "mode": "OFFLINE_NON_EXECUTING",
        "maximum_scenario_duration_ms": max(result["duration_ms"] for result in results),
        "results": results,
    }
    print("=" * 66)
    print(f" BENCHMARK RESULT: {passed_count} / {len(results)} SCENARIOS PASSED")
    print(" No live telemetry, diagnosis, health, or production-readiness claim is implied.")
    print("=" * 66)
    return report


if __name__ == "__main__":
    sys.exit(0 if run_benchmarks()["success"] else 1)
