#!/usr/bin/env python3
"""Deterministic, offline master validation gate for MNE_Brain Release 2."""

import json
import sys
from pathlib import Path
from typing import Any, Callable

import jsonschema

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.entity.build_entity_index import EntityIndexBuilder
from core.connectors.engine import MultiPlatformConnectorEngine
from core.connectors.registry import ConnectorRegistry
from core.transports.registry import TransportRegistry
from core.troubleshooting.engine import P8TroubleshootingEngine
from core.troubleshooting.p9_engine import P9DiagnosticEngine
from core.evidence.build_evidence_pack import EvidencePackBuilder
from core.execution.execution_engine import ExecutionEngine
from core.execution.p10_engine import P10ExecutionEngine
from core.conversation.engine import ConversationEngine
from core.llm.registry import ProviderRegistry
from core.tools.broker import ToolBroker
from core.tools.drivers.p10_write import PLATFORM_DRIVER_FAMILIES
from core.lifecycle.lifecycle_engine import KnowledgeLifecycleEngine
from core.incidents.case_manager import IncidentCaseManager
from core.llm.llm_adapter import LLMAdapter
from core.orchestration.incident_orchestrator import IncidentOrchestrator
from core.policy.policy_engine import PolicyEngine
from core.reasoning.investigation_planner import InvestigationPlanner
from core.remediation.remediation_engine import RemediationEngine
from core.runbooks.registry import RunbookRegistry
from core.router.route_query import QueryRouter
from core.tools.drivers.driver_factory import DriverFactory
from core.verification.live_verify import LiveVerificationEngine
from integrations.n8n.webhook_listener import WebhookAlertListener
from scripts.audit_canonical_knowledge import audit_knowledge
from scripts.validate_p0_containment import validate_p0_containment


def run_master_validation() -> dict[str, Any]:
    """Run 22 read-only gates and return a machine-readable report."""
    print("=" * 66)
    print(" MNE_Brain Release 2 - Offline Master Validation Gate")
    print("=" * 66)
    results: list[dict[str, Any]] = []

    def gate(number: int, name: str, check: Callable[[], tuple[bool, str]]) -> None:
        try:
            passed, detail = check()
        except Exception as exc:  # Validation must report a bounded failure, not crash.
            passed, detail = False, f"{type(exc).__name__}: {exc}"
        results.append({"gate": number, "name": name, "passed": bool(passed), "detail": detail})
        outcome = "PASS" if passed else "FAIL"
        print(f"[GATE {number:02d}/22] {name} -> {outcome}: {detail}")

    def governance_check() -> tuple[bool, str]:
        required = [
            base_dir / "AGENTS.md",
            base_dir / "00_meta" / "01_naming_conventions.md",
            base_dir / "docs" / "RELEASE_2_ARCHITECTURE.md",
            base_dir / "docs" / "SOURCE_OF_TRUTH.md",
        ]
        adrs = list((base_dir / "00_meta" / "adr").glob("ADR-*.md"))
        return all(path.is_file() for path in required) and len(adrs) >= 13, f"{len(adrs)} ADRs; {len(required)} required contracts"

    def schema_check() -> tuple[bool, str]:
        schema_paths = sorted((base_dir / "00_meta" / "schemas").glob("*.schema.json"))
        required_names = {
            "action.schema.json",
            "canonical-note.schema.json",
            "entity.schema.json",
            "evidence.schema.json",
            "incident-case.schema.json",
            "incident-intake.schema.json",
            "incident-workflow-governance.schema.json",
            "investigation.schema.json",
            "live-evidence.schema.json",
            "profile.schema.json",
            "runbook.schema.json",
            "connector-catalog.schema.json",
            "p7-transport-catalog.schema.json",
            "p7-device-bindings.schema.json",
            "p8-diagnostic-catalog.schema.json",
            "p9-diagnostic-catalog.schema.json",
            "p10-operation-catalog.schema.json",
            "p10-operation-parameters.schema.json",
            "p10-prepared-plan.schema.json",
            "p10-approval-request.schema.json",
            "p10-execution-result.schema.json",
            "p10-rollback-plan.schema.json",
            "p10-critical-warning.schema.json",
            "p10-platform-transaction.schema.json",
            "p10-check-result.schema.json",
            "owner-direct-risk-warning.schema.json",
            "owner-direct-identity-audit.schema.json",
            "conversation-thread.schema.json",
            "conversation-turn.schema.json",
            "conversation-message.schema.json",
            "provider-profile.schema.json",
            "provider-capabilities.schema.json",
            "tool-call.schema.json",
            "tool-approval.schema.json",
            "stream-event.schema.json",
            "external-ai-authorization.schema.json",
            "workspace-change-plan.schema.json",
            "workspace-rollback-plan.schema.json",
            "owner-full-control-coverage.schema.json",
            "task.schema.json",
        }
        for path in schema_paths:
            schema = json.loads(path.read_text(encoding="utf-8"))
            jsonschema.validators.validator_for(schema).check_schema(schema)
        names = {path.name for path in schema_paths}
        return names == required_names, f"{len(schema_paths)} required schemas are valid"

    def knowledge_check() -> tuple[bool, str]:
        report = audit_knowledge(
            base_dir / "knowledge",
            base_dir / "00_meta" / "schemas" / "canonical-note.schema.json",
        )
        statuses = report.get("status_counts", {})
        passed = report["compliant"] and report["notes_scanned"] == 48 and statuses == {"unverified": 48}
        return passed, f"{report['notes_scanned']} compliant notes; statuses={statuses}"

    router = QueryRouter(base_dir=base_dir)
    entity_builder = EntityIndexBuilder(base_dir=base_dir)
    evidence_builder = EvidencePackBuilder(base_dir=base_dir)

    def routing_check() -> tuple[bool, str]:
        exact = router.classify_query("Why is fw-fortigate-hq-01 unreachable?")
        concept = router.classify_query("Explain network segmentation principles")
        unknown = router.classify_query("Unknown mystery outage")
        passed = (
            exact["route_type"] == "troubleshoot"
            and exact["resolution_status"] == "exact"
            and exact["resolved_entity_ids"] == ["fw-fortigate-hq-01"]
            and concept["resolution_status"] == "not_required"
            and unknown["resolution_status"] == "unknown"
            and unknown["clarification_request"]["requires_clarification"] is True
        )
        return passed, "exact, concept, and unknown routes remain deterministic"

    def entity_check() -> tuple[bool, str]:
        index = entity_builder.build_index(persist=False)
        match = entity_builder.resolve_entity("172.23.70.4")
        passed = (
            index["total_entities"] == 48
            and len(match) == 1
            and match[0]["entity_id"] == "fw-fortigate-edge-01"
            and match[0]["knowledge_status"] == "unverified"
        )
        return passed, f"{index['total_entities']} in-memory entities; exact identity preserved"

    def evidence_check() -> tuple[bool, str]:
        targets = entity_builder.resolve_entity("172.23.70.4")
        pack = evidence_builder.build_evidence_pack("Check firewall status", targets, persist=False)
        passed = (
            pack["total_tokens"] <= pack["max_token_budget"] == 1500
            and pack["evidence_blocks"] == []
            and pack["sources"] == []
            and bool(pack["unknowns"])
        )
        return passed, f"{pack['total_tokens']} accepted tokens; unverified record retained as unknown"

    def reasoning_check() -> tuple[bool, str]:
        result = InvestigationPlanner().evaluate_investigation_state(
            [], [{"content": "Interface status down; link down."}]
        )
        passed = (
            result["reasoning_status"] == "PENDING_EVIDENCE"
            and result["stop_early_triggered"] is False
            and result["conclusive_root_cause"] is None
            and result["accepted_evidence_refs"] == []
        )
        return passed, "unattributed incident text cannot become a conclusion"

    def policy_check() -> tuple[bool, str]:
        policy = PolicyEngine(base_dir=base_dir)
        live_read = policy.evaluate_action_policy(0, is_live_verification=True)
        level_two = policy.evaluate_action_policy(2, action_id="offline-validation")
        level_four = policy.evaluate_action_policy(4, action_id="offline-validation")
        passed = (
            live_read["policy_status"] == "DISABLED_BY_POLICY"
            and level_two["policy_status"] == "OWNER_INSTRUCTION_REQUIRED"
            and level_four["policy_status"] == "CRITICAL_EXCEPTION_ONLY"
            and not live_read["approved"]
            and not level_two["approved"]
            and not level_four["approved"]
        )
        return passed, "live reads disabled; Level 2 needs owner instruction and Level 4 needs the P10 critical path"

    def verification_check() -> tuple[bool, str]:
        verifier = LiveVerificationEngine(base_dir=base_dir)
        plan = verifier.build_verification_plan("fortigate_edge")
        unauthorized = verifier.execute_live_verification("fortigate_edge")
        authorized = verifier.execute_live_verification("fortigate_edge", authorized=True)
        passed = (
            plan["status"] == "PLANNED"
            and plan["connection_attempted"] is False
            and unauthorized["status"] == "NOT_RUN"
            and authorized["status"] == "NOT_CONFIGURED"
            and authorized["trust_level"] == 0
            and authorized["connection_attempted"] is False
        )
        return passed, "plans are non-connecting; authorization cannot invent telemetry"

    def lifecycle_check() -> tuple[bool, str]:
        target = entity_builder.resolve_entity("172.23.70.4")[0]
        result = KnowledgeLifecycleEngine(base_dir=base_dir).detect_knowledge_drift(
            target["entity_id"], target["canonical_file"], {"observed_facts": {"status": "up"}}, persist=False
        )
        passed = result["status"] == "CANONICAL_NOT_ACCEPTED" and result["persistence"] == "NOT_REQUESTED"
        return passed, "unverified canonical knowledge cannot be drift-promoted"

    def llm_check() -> tuple[bool, str]:
        pack = evidence_builder.build_evidence_pack("Check firewall status", entity_builder.resolve_entity("172.23.70.4"))
        response = LLMAdapter(provider="local_fallback", base_dir=base_dir).generate_response("Check firewall status", pack)
        passed = (
            response["status"] == "SUCCESS"
            and response["evidence_status"] == "INSUFFICIENT_EVIDENCE"
            and response["trust_level"] == 0
            and response["external_call_attempted"] is False
            and response["sources"] == []
        )
        return passed, "local formatter reports insufficient evidence without outbound calls"

    def execution_check() -> tuple[bool, str]:
        calls: list[tuple[str, str]] = []

        def forbidden_driver(platform: str, command: str) -> dict[str, str]:
            calls.append((platform, command))
            return {"status": "SUCCESS"}

        result = ExecutionEngine(base_dir=base_dir).execute_action(
            {
                "action_id": "offline-validation-read",
                "platform": "offline",
                "command": "show status",
                "risk_level": 0,
                "pre_checks": [],
                "post_checks": [],
            },
            forbidden_driver,
            owner_reference="MNE-BRAIN-OWNER",
            explicit_owner_instruction=True,
            persist_audit=False,
        )
        passed = result["status"] == "EXECUTION_DISABLED" and result["attempts"] == 0 and not calls and result["audit_persisted"] is False
        return passed, "disabled execution never invokes the callback or persists audit"

    def drivers_check() -> tuple[bool, str]:
        factory = DriverFactory()
        targets = {
            "ssh": "192.0.2.10",
            "rest": "https://example.invalid/status",
            "powershell": "localhost",
            "winrm": "192.0.2.20",
            "vmware": "vcenter.example.invalid",
            "sql": "sql.example.invalid",
            "snmp": "192.0.2.30",
        }
        plans = [factory.plan_command(protocol, target, "read-status") for protocol, target in targets.items()]
        passed = all(
            plan["status"] == "PLANNED"
            and plan["connection_attempted"] is False
            and plan["output"] is None
            and "operation_fingerprint" in plan
            for plan in plans
        )
        return passed, f"{len(plans)} protocol plans are bounded and non-connecting"

    def remediation_check() -> tuple[bool, str]:
        calls: list[tuple[str, str]] = []

        def forbidden_driver(platform: str, command: str) -> dict[str, str]:
            calls.append((platform, command))
            return {"status": "SUCCESS"}

        engine = RemediationEngine(base_dir=base_dir)
        ordinary = engine.execute_remediation("level0-read-telemetry", forbidden_driver)
        prohibited = engine.execute_remediation("level4-emergency-firewall-change", forbidden_driver)
        serialized = json.dumps({"ordinary": ordinary, "prohibited": prohibited})
        passed = (
            ordinary["status"] == "BLOCKED"
            and prohibited["status"] == "BLOCKED"
            and prohibited["remediation_plan"]["status"] == "CRITICAL_EXCEPTION_REQUIRED"
            and ordinary["driver_invoked"] is False
            and prohibited["driver_invoked"] is False
            and not calls
            and '"command"' not in serialized
            and '"rollback_command"' not in serialized
        )
        return passed, "unreviewed actions cannot execute; legacy Level 4 redirects to the P10 critical path"

    def p10_readiness_check() -> tuple[bool, str]:
        engine = P10ExecutionEngine(base_dir=base_dir)
        metadata = engine.catalog.list_metadata()
        passed = (
            metadata["family_count"] == 7
            and metadata["template_count"] == 56
            and metadata["action_variant_count"] == 176
            and len(PLATFORM_DRIVER_FAMILIES) == 8
            and engine.execution_enabled is False
            and engine.policy["level_4_policy"] == "CRITICAL_EXCEPTION_ONLY"
            and engine.policy["audit_mode"] == "IN_MEMORY_ONLY"
            and engine.policy["retention"] == "NONE"
            and all(engine.policy[key] is False for key in ("ticketing_enabled", "paging_enabled", "notifications_enabled", "automatic_assignment_enabled", "automatic_remediation_enabled"))
        )
        return passed, "7 families, 56 templates, 176 action variants; P10 execution disabled at rest"

    def p11_control_plane_check() -> tuple[bool, str]:
        providers = ProviderRegistry(base_dir).list_profiles()
        engine = ConversationEngine(base_dir)
        thread = engine.create_thread(title="P11 offline gate")
        turn = engine.start_turn(thread["thread_id"], content="offline deterministic check", run_async=False)
        broker = ToolBroker(base_dir)
        modules = {path.name for path in (base_dir / "gui/scripts").glob("*.js")}
        required_modules = {"api.js", "auth.js", "threads.js", "composer.js", "streaming.js", "activity.js", "evidence.js", "tool_calls.js", "approvals.js", "providers.js", "p10.js"}
        passed = (
            len(providers) == 7
            and {profile["provider_type"] for profile in providers if profile["enabled"]} == {"codex_app_server", "opencode", "deterministic_local"}
            and turn["status"] == "COMPLETED"
            and not broker.p7_live_enabled
            and not broker.p10.execution_enabled
            and modules == required_modules
        )
        return passed, "7 provider profiles including Codex App Server and OpenCode; local fallback lifecycle passed; P7/P10 live execution disabled; 11 GUI modules"

    def presentation_automation_check() -> tuple[bool, str]:
        html = (base_dir / "gui" / "index.html").read_text(encoding="utf-8")
        forbidden_routes = ("/actions/execute", "/knowledge/promote", "/automation/trigger", "/settings", "/oauth/")
        alert_result = WebhookAlertListener(base_dir=base_dir).process_alert_payload({})
        passed = (
            "ZERO Business Logic in GUI" in html
            and not any(route in html for route in forbidden_routes)
            and "innerHTML" not in html
            and alert_result["status"] == "INGESTION_DISABLED"
            and alert_result["accepted"] is False
        )
        return passed, "GUI is presentation-only and alert ingestion is disabled"

    def orchestration_check() -> tuple[bool, str]:
        result = IncidentOrchestrator(base_dir=base_dir).investigate(
            "Why is fw-fortigate-hq-01 unreachable?"
        )
        passed = (
            result["status"] == "EVIDENCE_REQUIRED"
            and result["target"]["entity_id"] == "fw-fortigate-hq-01"
            and result["target"]["operational_state"] == "UNKNOWN"
            and result["reasoning"]["conclusive_root_cause"] is None
            and 0 < len(result["next_checks"]) <= 5
            and result["metrics"]["handoff_chars"] <= 6000
            and not any(result["safety"].values())
        )
        return passed, "exact target, bounded AI handoff, and evidence objectives remain offline"

    def incident_case_check() -> tuple[bool, str]:
        result = IncidentCaseManager(base_dir=base_dir).build_case(
            "Why is nablus-branch unreachable?",
            impact_context={"affected_scope": "branch", "availability": "unavailable"},
        )
        passed = (
            result["case_state"] == "AWAITING_EVIDENCE"
            and result["priority"]["classification"] == "PROVISIONAL_P2"
            and result["priority"]["owner_confirmation_required"] is True
            and result["impact"]["status"] == "REPORTED_NOT_VERIFIED"
            and result["ownership"]["routing_status"] == "OWNER_CONTROLLED_NOT_NOTIFIED"
            and result["ownership"]["primary"]["team"] == "MNE-BRAIN-OWNER"
            and result["response_target"]["status"] == "NO_CONFIGURED_RESPONSE_TARGET"
            and not any(result["safety"].values())
        )
        return passed, "reported impact, provisional priority, owner handoff, and no-SLA state remain offline"

    def runbook_intelligence_check() -> tuple[bool, str]:
        registry = RunbookRegistry(base_dir=base_dir)
        entities = entity_builder.build_index(persist=False)["entities"]
        coverage = registry.coverage_report(entities)
        selection = registry.select_for_target(entity_builder.resolve_entity("waf-f5-bigip-01")[0])
        passed = (
            registry.build_registry()["total_runbooks"] == 12
            and coverage["context_covered_entities"] == coverage["total_entities"] == 48
            and coverage["operationally_covered_entities"] == 48
            and coverage["operational_runbook_readiness"] is True
            and coverage["production_readiness_claimed"] is False
            and selection["candidates"][0]["runbook_id"] == "p5-published-service-triage"
            and selection["operational_use_allowed"] is True
            and selection["selection_status"] == "OWNER_REVIEWED_GUIDANCE_AVAILABLE"
            and selection["body_included"] is False
            and not any(
                selection[key]
                for key in (
                    "live_connection_attempted",
                    "external_ai_call_attempted",
                    "notification_sent",
                    "persistence_attempted",
                    "remediation_attempted",
                )
            )
        )
        return passed, "48 entities have context and owner-reviewed procedures; production remains unclaimed"

    def p0_containment_check() -> tuple[bool, str]:
        report = validate_p0_containment()
        passed = (
            report["success"]
            and report["passed"] == report["total"] == 5
            and report["secret_values_read"] is False
            and report["secret_values_printed"] is False
        )
        return passed, f"{report['passed']}/{report['total']} Git-containment checks; no secret values read"

    def connector_readiness_check() -> tuple[bool, str]:
        registry = ConnectorRegistry(base_dir=base_dir)
        coverage = registry.coverage_report()
        engine = MultiPlatformConnectorEngine(base_dir=base_dir)
        plan = engine.plan("fmc-cisco-hq-01")
        fixture = engine.validate_offline_fixture("fmc-cisco-hq-01", ["server_version"])
        live = engine.execute_readonly("fmc-cisco-hq-01", ["server_version"], authorized=True)
        p7 = TransportRegistry(base_dir=base_dir).public_status()
        p8 = P8TroubleshootingEngine(base_dir=base_dir)
        p8_status = p8.status()
        p8_plan = p8.plan({"scenario_id": "p8-vpn-access", "binding_id": "p7-fortigate-edge", "symptom": "vpn down"})
        p9 = P9DiagnosticEngine(base_dir=base_dir)
        p9_status = p9.status()
        p9_plan = p9.plan({"scenario_id": "p9-vpn-access", "binding_id": "p7-fortigate-edge", "symptom": "vpn down"})
        bindings = p7["credential_bindings"]
        passed = (
            registry.public_catalog()["total_connectors"] == 15
            and coverage["total_entities"] == coverage["planned_entities"] == coverage["offline_validated_entities"] == 48
            and coverage["planning_coverage_percent"] == coverage["offline_validation_coverage_percent"] == 100.0
            and coverage["live_transport_entities"] == 1
            and coverage["live_collection_enabled"] is False
            and coverage["production_readiness_claimed"] is False
            and plan["status"] == "PLANNED_READ_ONLY"
            and plan["raw_operations_included"] is False
            and fixture["status"] == "SIMULATED_NOT_ACCEPTED"
            and fixture["trust_level"] == 0
            and fixture["connection_attempted"] is False
            and live["reason"] == "P6_LIVE_TRANSPORTS_DISABLED"
            and live["connection_attempted"] is False
            and p7["total_entities"] == p7["transport_implementation_coverage"] == 48
            and p7["transport_implementation_coverage_percent"] == 100.0
            and len(p7["drivers"]) == 7
            and p7["live_enabled"] is False
            and p7["audit_mode"] == "IN_MEMORY_ONLY"
            and p7["retention"] == "NONE"
            and p7["persistence_enabled"] is False
            and p7["remediation_enabled"] is False
            and bindings["total_bindings"] == 62
            and bindings["active_bindings"] == 61
            and bindings["owner_excluded_bindings"] == 1
            and bindings["identity_pinned_bindings"] == 50
            and bindings["kerberos_bindings"] == 8
            and bindings["permanent_mapping_complete"] is True
            and p8_status["scenario_count"] == 8
            and p8_status["reconciliation_count"] == 62
            and p8_status["live_enabled"] is False
            and p8_plan["status"] == "EVIDENCE_REQUIRED"
            and 1 <= len(p8_plan["planned_checks"]) <= 3
            and p8_plan["root_cause"] is None
            and not any(p8_plan["safety"].values())
            and p9_status["scenario_count"] == 8
            and p9_status["check_count"] == 30
            and p9_status["live_enabled"] is False
            and p9_plan["status"] == "EVIDENCE_REQUIRED"
            and p9_plan["root_cause"] is None
            and not any(p9_plan["safety"].values())
        )
        return passed, "P6-P8 coverage remains intact; P9 has eight deep-diagnostic scenarios and 30 checks while live state remains disabled"

    gate(1, "Governance and ADR contracts", governance_check)
    gate(2, "Schema syntax contracts", schema_check)
    gate(3, "Canonical knowledge metadata", knowledge_check)
    gate(4, "Deterministic query routing", routing_check)
    gate(5, "Entity identity and truth status", entity_check)
    gate(6, "Bounded evidence retrieval", evidence_check)
    gate(7, "Evidence-gated reasoning", reasoning_check)
    gate(8, "Policy and risk gates", policy_check)
    gate(9, "Non-executing live verification", verification_check)
    gate(10, "Review-only knowledge lifecycle", lifecycle_check)
    gate(11, "Local evidence-safe answer layer", llm_check)
    gate(12, "Disabled execution state machine", execution_check)
    gate(13, "Non-connecting protocol drivers", drivers_check)
    gate(14, "Planning-only remediation", remediation_check)
    gate(15, "Presentation and alert boundaries", presentation_automation_check)
    gate(16, "P3 incident orchestration", orchestration_check)
    gate(17, "P4 incident case management", incident_case_check)
    gate(18, "P5 runbook intelligence", runbook_intelligence_check)
    gate(19, "P6-P9 connector and troubleshooting readiness", connector_readiness_check)
    gate(20, "P0 simple local-secret containment", p0_containment_check)
    gate(21, "P10 owner-controlled write readiness", p10_readiness_check)
    gate(22, "P11 conversation, provider, and tool control plane", p11_control_plane_check)

    passed_count = sum(result["passed"] for result in results)
    report = {
        "success": passed_count == len(results) == 22,
        "passed": passed_count,
        "total": len(results),
        "mode": "OFFLINE_NON_EXECUTING",
        "results": results,
    }
    print("=" * 66)
    print(f" MASTER VALIDATION: {passed_count} / {len(results)} GATES PASSED")
    print(" Operational readiness is not claimed by this offline result.")
    print("=" * 66)
    return report


if __name__ == "__main__":
    sys.exit(0 if run_master_validation()["success"] else 1)
