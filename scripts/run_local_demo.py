#!/usr/bin/env python3
"""
MNE_Brain Release 2 — Local Interactive Execution Console (`scripts/run_local_demo.py`)
Runs an end-to-end operational query locally through the complete 8-stage Brain pipeline.
"""

import sys
import json
import argparse
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.router.route_query import QueryRouter
from core.entity.build_entity_index import EntityIndexBuilder
from core.evidence.build_evidence_pack import EvidencePackBuilder
from core.reasoning.investigation_planner import InvestigationPlanner
from core.policy.policy_engine import PolicyEngine
from core.verification.live_verify import LiveVerificationEngine
from core.lifecycle.lifecycle_engine import KnowledgeLifecycleEngine
from core.llm.llm_adapter import LLMAdapter
from core.tools.drivers.driver_factory import DriverFactory
from core.observability.tracer import ObservabilityTracer

def run_local_query(question: str):
    tracer = ObservabilityTracer(base_dir=base_dir)
    print("==================================================")
    print(" MNE_Brain Release 2 — Local Pipeline Execution")
    print(f" Correlation ID: {tracer.correlation_id}")
    print(f" User Question:  \"{question}\"")
    print("==================================================\n")

    # 1. Query Router
    router = QueryRouter(base_dir=base_dir)
    route_res = router.classify_query(question)
    print(f"[STAGE 1: QUERY ROUTER] Route Type: '{route_res['route_type']}', Task Target: '{route_res['task_target']}'")
    tracer.trace_step("query_router", "classify_query", details=route_res)

    # Disambiguation Check
    if route_res.get("clarification_request") and route_res["clarification_request"]["requires_clarification"]:
        print("\n⚠️ [INTERACTIVE DISAMBIGUATION TRIGGERED]")
        print(route_res["clarification_request"]["prompt"])
        for opt in route_res["clarification_request"]["options"]:
            print(f" [{opt['option_number']}] {opt['name']} ({opt['entity_id']})")
        print("\nPlease specify a target entity from the options above.\n")
        return

    # 2. Entity Resolver
    entity_builder = EntityIndexBuilder(base_dir=base_dir)
    entities = entity_builder.resolve_entity(question)
    print(f"[STAGE 2: ENTITY RESOLVER] Matched Entities ({len(entities)}): {[e['name'] for e in entities]}")
    tracer.trace_step("entity_resolver", "resolve_entity", details={"matched": len(entities)})

    # 3. Evidence Pack Builder
    ev_builder = EvidencePackBuilder(base_dir=base_dir)
    evidence = ev_builder.build_evidence_pack(question, target_entities=entities)
    print(f"[STAGE 3: EVIDENCE PACK] Context Bounded Tokens: {evidence['total_tokens']} / 1500 (Sources: {len(evidence['sources'])})")
    tracer.trace_step("evidence_builder", "build_evidence_pack", details={"tokens": evidence['total_tokens']})

    # 4. Reasoning Engine
    planner = InvestigationPlanner()
    reason_eval = planner.evaluate_investigation_state([], evidence["evidence_blocks"])
    print(f"[STAGE 4: REASONING ENGINE] Information Gain: {reason_eval['information_gain']} bits (Stop Early: {reason_eval['stop_early_triggered']})")
    tracer.trace_step("reasoning_engine", "evaluate_state", details=reason_eval)

    # 5. Policy Engine
    policy_engine = PolicyEngine(base_dir=base_dir)
    has_current_live_evidence = any(
        block.get("evidence_status") == "live_verified"
        for block in evidence.get("evidence_blocks", [])
    )
    policy_res = policy_engine.evaluate_verification_necessity(
        route_res["route_type"], has_current_live_evidence=has_current_live_evidence
    )
    print(f"[STAGE 5: POLICY ENGINE] Verification Necessity: {policy_res['reason']} (Requires Live Verify: {policy_res['live_verification_required']})")
    tracer.trace_step("policy_engine", "evaluate_policy", details=policy_res)

    # 6. Live Verification
    target_prof = "fortigate" if "fortigate" in question.lower() else ("cisco" if "cisco" in question.lower() else "vmware")
    if policy_res["live_verification_allowed"]:
        verifier = LiveVerificationEngine(base_dir=base_dir)
        verify_res = verifier.execute_live_verification(target_prof, authorized=True)
    else:
        verify_res = {
            "status": "NOT_RUN",
            "profile_name": target_prof,
            "trust_level": 0,
            "checks_executed": 0,
            "reason": policy_res["policy_reason"],
        }
    print(f"[STAGE 6: LIVE VERIFICATION] Status: {verify_res['status']} ({verify_res['reason']})")
    tracer.trace_step("live_verification", "verification_gate", details=verify_res)

    # 7. Knowledge Lifecycle Engine
    lifecycle = KnowledgeLifecycleEngine(base_dir=base_dir)
    drift_res = lifecycle.detect_knowledge_drift("fw-fortigate-hq-01", "knowledge/topology/fortigate-canonical.md", "status: ok")
    print(f"[STAGE 7: KNOWLEDGE LIFECYCLE] Drift Detected: {drift_res['drift_detected']} (Zero Auto-Overwrite Enforced)")
    tracer.trace_step("lifecycle_engine", "detect_drift", details=drift_res)

    # 8. Tool Engine Driver Execution & LLM Response Generation
    factory = DriverFactory()
    drv_res = factory.execute_command("powershell", "localhost", "Get-Date")
    print(f"[STAGE 8: DRIVER EXECUTION] Protocol: 'powershell', Status: {drv_res['status']}")

    llm = LLMAdapter(provider="local_fallback", base_dir=base_dir)
    final_res = llm.generate_response(question, evidence)

    print("\n==================================================")
    print(" FINAL EVIDENCE-GROUNDED RESPONSE")
    print("==================================================")
    print(final_res["response_text"].encode('ascii', 'replace').decode('ascii'))
    print("==================================================")
    print(f" Correlation Trace Saved to: operations/logs/observability.jsonl\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MNE_Brain Local Interactive Console")
    parser.add_argument("--question", default="What is the status of FortiGate core firewall at 172.23.19.1?", help="Infrastructure query string")
    args = parser.parse_args()

    run_local_query(args.question)
