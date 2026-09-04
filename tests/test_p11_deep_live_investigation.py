from __future__ import annotations

import hashlib
from pathlib import Path

from core.entity.build_entity_index import EntityIndexBuilder
from core.investigation.planner import InvestigationPlanner
from core.conversation.engine import ConversationEngine
from core.llm.contracts import ProviderEvent
from core.llm.registry import ProviderRegistry
from core.tools.broker import ToolBroker
from scripts.run_p7_authenticated_baseline import AuthenticatedBaselineRunner


BASE = Path(__file__).resolve().parents[1]


class _PolicyRunner:
    def run_exact(self, *, owner_proceed, binding_id, target, check_id):
        assert owner_proceed is True
        assert target == "172.23.70.4"
        facts = (
            [{"object_name": "MAIL-84", "subnet": ["172.23.71.84", "255.255.255.255"]}]
            if check_id == "firewall_addresses"
            else [{"policy_id": "310", "name": ["Mail-Internet"], "srcaddr": ["MAIL-84"], "dstaddr": ["all"], "action": ["accept"], "nat": ["enable"]}]
        )
        return {
            "status": "COMPLETE",
            "results": [{"status": "SUCCESS", "connection_attempted": True, "normalized_facts": facts}],
        }


def test_unknown_explicit_ip_never_fuzzy_matches_unrelated_entity():
    query = "what is the fortigate policy for server 172.23.71.84"
    assert EntityIndexBuilder(BASE).resolve_entity(query) == []


def test_policy_by_ip_plan_has_two_exact_read_only_steps():
    plan = InvestigationPlanner(BASE).plan("deep live check fortigate internet policy for 172.23.71.84")
    assert plan["intent"] == "fortigate_policy_lookup"
    assert [item["check_id"] for item in plan["candidates"]] == ["firewall_addresses", "firewall_policies"]
    assert all(item["target"] == "172.23.70.4" and item["read_only"] for item in plan["candidates"])
    assert plan["writes_allowed"] is False and plan["operations_included"] is False


def test_named_server_policy_question_also_gets_two_live_steps():
    plan = InvestigationPlanner(BASE).plan("what is the FortiGate policy used by WSUS server to access internet")
    assert plan["intent"] == "fortigate_policy_lookup"
    assert plan["subject_ips"] == [] and "wsus" in plan["subject_terms"]
    assert [item["check_id"] for item in plan["candidates"]] == ["firewall_addresses", "firewall_policies"]


def test_fortigate_output_is_structured_without_returning_raw_device_text():
    addresses = '''config firewall address
    edit "MAIL-84"
        set subnet 172.23.71.84 255.255.255.255
    next
end'''
    policies = '''config firewall policy
    edit 310
        set name "Mail Internet"
        set srcaddr "MAIL-84"
        set dstaddr "all"
        set action accept
        set service "ALL"
        set nat enable
    next
end'''
    assert AuthenticatedBaselineRunner._normalized_facts("firewall_addresses", addresses) == [
        {"object_name": "MAIL-84", "subnet": ["172.23.71.84", "255.255.255.255"]}
    ]
    assert AuthenticatedBaselineRunner._normalized_facts("firewall_policies", policies)[0]["policy_id"] == "310"


def test_owner_session_can_execute_both_planned_reads_and_receive_normalized_facts():
    broker = ToolBroker(BASE, p7_scoped_available=True, p7_runner=_PolicyRunner())
    plan = InvestigationPlanner(BASE).plan("fortigate policy used by 172.23.71.84")
    digest = hashlib.sha256(b"owner-session").hexdigest()
    outputs = []
    for candidate in plan["candidates"]:
        arguments = {key: candidate[key] for key in ("binding_id", "target", "check_id")}
        outputs.append(broker.run_owner_autonomous_live_read(arguments, owner_session_digest=digest))
    assert [item["status"] for item in outputs] == ["LIVE_VERIFIED", "LIVE_VERIFIED"]
    assert outputs[0]["normalized_facts"][0]["object_name"] == "MAIL-84"
    assert outputs[1]["normalized_facts"][0]["policy_id"] == "310"
    assert all(item["raw_output_included"] is False and item["credentials_returned"] is False for item in outputs)


def test_conversation_loop_performs_two_live_steps_then_forces_grounded_answer():
    registry = ProviderRegistry(BASE)

    class _DeepGateway:
        def __init__(self):
            self.registry = registry
            self.calls = 0

        def stream(self, _provider_id, context, *, tools, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                assert "fortigate_policy_lookup" in context[0]["content"]
                yield ProviderEvent("tool_proposal", {"name": "mne.prepare_live_read", "arguments": {"binding_id": "p7-fortigate-edge-addresses", "target": "172.23.70.4", "check_id": "firewall_addresses"}})
            elif self.calls == 2:
                assert "MAIL-84" in context[-1]["content"]
                yield ProviderEvent("tool_proposal", {"name": "mne.prepare_live_read", "arguments": {"binding_id": "p7-fortigate-edge-policies", "target": "172.23.70.4", "check_id": "firewall_policies"}})
            else:
                assert tools == [] and '"policy_id"' in context[-1]["content"] and '"310"' in context[-1]["content"]
                yield ProviderEvent("text_delta", {"text": "Live verified: policy 310 (Mail-Internet) allows MAIL-84 with NAT enabled."})
            yield ProviderEvent("completed", {"finish_reason": "stop"})

    broker = ToolBroker(BASE, p7_scoped_available=True, p7_runner=_PolicyRunner())
    gateway = _DeepGateway()
    engine = ConversationEngine(BASE, gateway=gateway, tool_broker=broker)
    thread = engine.create_thread(title="deep live", permission_mode="OWNER_AUTONOMOUS")
    turn = engine.start_turn(
        thread["thread_id"],
        content="deep live check: what FortiGate policy allows internet for 172.23.71.84?",
        owner_session_digest="a" * 64,
        run_async=False,
    )
    assert turn["status"] == "COMPLETED" and gateway.calls == 3
    message = engine.store.get_thread(thread["thread_id"])["messages"][-1]
    assert "policy 310" in message["content"] and len(message["evidence_refs"]) == 2
    events = engine.events.list_after(turn["turn_id"])
    assert any(item["event_type"] == "investigation.planned" for item in events)
    assert sum(item["event_type"] == "tool.completed" for item in events) == 2


def test_two_live_proposals_in_one_provider_round_preserve_both_results():
    registry = ProviderRegistry(BASE)

    class _ParallelProposalGateway:
        def __init__(self):
            self.registry = registry
            self.calls = 0

        def stream(self, _provider_id, context, *, tools, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                yield ProviderEvent("tool_proposal", {"name": "mne.prepare_live_read", "arguments": {"binding_id": "p7-fortigate-edge-addresses", "target": "172.23.70.4", "check_id": "firewall_addresses"}})
                yield ProviderEvent("tool_proposal", {"name": "mne.prepare_live_read", "arguments": {"binding_id": "p7-fortigate-edge-policies", "target": "172.23.70.4", "check_id": "firewall_policies"}})
            else:
                assert tools == [] and "MAIL-84" in context[-1]["content"] and '"policy_id"' in context[-1]["content"]
                yield ProviderEvent("text_delta", {"text": "Policy 310 is live verified."})
            yield ProviderEvent("completed", {"finish_reason": "stop"})

    broker = ToolBroker(BASE, p7_scoped_available=True, p7_runner=_PolicyRunner())
    engine = ConversationEngine(BASE, gateway=_ParallelProposalGateway(), tool_broker=broker)
    thread = engine.create_thread(title="multi-proposal", permission_mode="OWNER_AUTONOMOUS")
    turn = engine.start_turn(
        thread["thread_id"], content="FortiGate internet policy for 172.23.71.84",
        owner_session_digest="d" * 64, run_async=False,
    )
    assert turn["status"] == "COMPLETED"
    assert len(engine.store.get_thread(thread["thread_id"])["messages"][-1]["evidence_refs"]) == 2
