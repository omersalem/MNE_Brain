"""Offline and security validation for the complete P11 control plane."""

from __future__ import annotations

import http.client
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema
import pytest

from core.api.security import OwnerCredentialVerifier, OwnerSessionError, OwnerSessionManager
from core.api.server import BoundedThreadingHTTPServer, MNEBrainAPIHandler
from core.conversation.cancellation import CancellationToken, TurnCancelled, TurnTimedOut
from core.conversation.engine import ConversationEngine
from core.conversation.event_stream import EventStream
from core.credentials.store import CredentialStore
from core.codex.app_server import CODEX_PROVIDER_ID
from core.llm.capability_policy import CapabilityPolicy
from core.llm.contracts import CANONICAL_PROVIDER_EVENTS, ProviderEvent, ProviderRequest
from core.llm.external_authorization import ExternalAuthorizationError, ExternalAuthorizationManager, ExternalDataPolicy
from core.llm.providers import AnthropicProvider, DeterministicLocalProvider, OllamaProvider, OpenAIProvider
from core.llm.providers.base import SAFE_PROVIDER_ERRORS
from core.llm.registry import ProviderRegistry, ProviderRegistryError
from core.opencode import OPENCODE_PROVIDER_ID
from core.tools.broker import ToolBroker, ToolBrokerError
from core.tools.command_policy import CommandPolicy, CommandPolicyError
from core.tools.permissions import ToolPermissionError, ToolPermissions
from core.tools.workspace_boundary import WorkspaceBoundary, WorkspaceBoundaryError


BASE = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("provider_id", [CODEX_PROVIDER_ID, OPENCODE_PROVIDER_ID])
@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("hello", "Hello! How can I help?"),
        ("what is the ip of main fortigate", "172.23.70.4"),
        ("ip of the main core switch", "172.23.70.254"),
    ],
)
def test_agent_engines_use_local_fast_path_for_bounded_answers(provider_id, prompt, expected):
    engine = ConversationEngine(BASE)
    invoked = []
    engine.codex.start_turn = lambda **kwargs: invoked.append(kwargs)
    engine.opencode.start_turn = lambda **kwargs: invoked.append(kwargs)
    thread = engine.create_thread(title="Fast answer", provider_id=provider_id, permission_mode="OWNER_AUTONOMOUS")

    turn = engine.start_turn(
        thread["thread_id"], content=prompt, owner_session_digest="a" * 64, run_async=False,
    )

    assert turn["status"] == "COMPLETED" and invoked == []
    answer = engine.store.get_thread(thread["thread_id"])["messages"][-1]["content"]
    assert expected in answer
    events = engine.events.list_after(turn["turn_id"])
    assert [event["event_type"] for event in events] == [
        "turn.started", "evidence.accepted", "answer.final", "turn.completed",
    ]
    assert events[-1]["redacted_payload"]["provider_invoked"] is False


def test_explicit_live_ip_question_still_uses_selected_agent_harness():
    engine = ConversationEngine(BASE)
    invoked = []

    def complete(**kwargs):
        invoked.append(kwargs)
        engine._codex_completed(kwargs["gui_thread_id"], kwargs["gui_turn_id"], "Live investigation completed.")

    engine.codex.start_turn = complete
    thread = engine.create_thread(title="Live answer", provider_id=CODEX_PROVIDER_ID, permission_mode="OWNER_AUTONOMOUS")
    turn = engine.start_turn(
        thread["thread_id"], content="verify the current ip of main fortigate live",
        owner_session_digest="a" * 64, run_async=False,
    )

    assert turn["status"] == "COMPLETED" and len(invoked) == 1


def test_unresolved_ip_question_falls_back_to_selected_agent_harness():
    engine = ConversationEngine(BASE)
    invoked = []

    def complete(**kwargs):
        invoked.append(kwargs)
        engine._codex_completed(
            kwargs["gui_thread_id"], kwargs["gui_turn_id"],
            "I investigated but could not identify that switch.",
        )

    engine.codex.start_turn = complete
    thread = engine.create_thread(title="Unresolved target", provider_id=CODEX_PROVIDER_ID)
    turn = engine.start_turn(
        thread["thread_id"], content="ip of the imaginary orbital switch",
        owner_session_digest="a" * 64, run_async=False,
    )

    assert turn["status"] == "COMPLETED" and len(invoked) == 1
    events = engine.events.list_after(turn["turn_id"])
    assert events[0]["redacted_payload"]["agent_harness"] == "CODEX_APP_SERVER"


def test_p11_schemas_and_adr_are_strict():
    names = {
        "conversation-thread.schema.json", "conversation-turn.schema.json", "conversation-message.schema.json",
        "provider-profile.schema.json", "provider-capabilities.schema.json", "tool-call.schema.json",
        "tool-approval.schema.json", "stream-event.schema.json", "external-ai-authorization.schema.json",
        "workspace-change-plan.schema.json", "workspace-rollback-plan.schema.json",
    }
    for name in names:
        schema = json.loads((BASE / "00_meta/schemas" / name).read_text(encoding="utf-8"))
        jsonschema.Draft7Validator.check_schema(schema)
        assert schema.get("additionalProperties") is False
    adr = (BASE / "00_meta/adr/ADR-018-P11-Conversation-Provider-Tool-Control-Plane.md").read_text(encoding="utf-8")
    assert "infrastructure writes" in adr.casefold() and "only through p10" in adr.casefold()


def test_owner_session_cookie_csrf_replay_and_expiry():
    clock = [1000.0]
    manager = OwnerSessionManager(inactivity_seconds=10, now=lambda: clock[0])
    payload, cookie = manager.create(client_host="127.0.0.1", host_header="localhost:8080", origin_header="http://localhost:8080")
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie and payload["mutation_nonce_required"]
    manager.authorize_mutation(client_host="::1", host_header="localhost:8080", origin_header="http://localhost:8080", cookie_header=cookie, csrf_token=payload["csrf_token"], nonce="a" * 20)
    with pytest.raises(OwnerSessionError, match="replay"):
        manager.authorize_mutation(client_host="127.0.0.1", host_header="localhost:8080", origin_header="http://localhost:8080", cookie_header=cookie, csrf_token=payload["csrf_token"], nonce="a" * 20)
    with pytest.raises(OwnerSessionError, match="CSRF"):
        manager.authorize_mutation(client_host="127.0.0.1", host_header="localhost:8080", origin_header="http://localhost:8080", cookie_header=cookie, csrf_token="wrong", nonce="b" * 20)
    clock[0] += 11
    with pytest.raises(OwnerSessionError, match="expired"):
        manager.require(client_host="127.0.0.1", host_header="localhost:8080", origin_header="http://localhost:8080", cookie_header=cookie)


def test_owner_session_rejects_non_loopback_and_cross_origin():
    manager = OwnerSessionManager()
    with pytest.raises(OwnerSessionError):
        manager.create(client_host="10.0.0.4", host_header="10.0.0.4:8080", origin_header="http://10.0.0.4:8080")
    with pytest.raises(OwnerSessionError):
        manager.create(client_host="127.0.0.1", host_header="localhost:8080", origin_header="http://localhost:9999")


def test_owner_password_login_is_hashed_limited_and_logout_revokes_session():
    clock = [1000.0]
    owner_candidate = "correct horse battery staple"
    wrong_candidate = "incorrect candidate value"
    hashed = OwnerCredentialVerifier.hash_password(owner_candidate, iterations=300_000, salt=b"owner-auth-test-salt-0001")
    verifier = OwnerCredentialVerifier(username="owner", password_hash=hashed)
    assert verifier.configured and "correct horse" not in hashed
    manager = OwnerSessionManager(credential_verifier=verifier, maximum_failures=3, lockout_seconds=30, now=lambda: clock[0])
    for _ in range(3):
        with pytest.raises(OwnerSessionError, match="invalid"):
            manager.login(username="owner", password=wrong_candidate, client_host="127.0.0.1", host_header="localhost:8080", origin_header="http://localhost:8080")
    with pytest.raises(OwnerSessionError, match="locked"):
        manager.login(username="owner", password=owner_candidate, client_host="127.0.0.1", host_header="localhost:8080", origin_header="http://localhost:8080")
    clock[0] += 31
    payload, cookie = manager.login(username="owner", password=owner_candidate, client_host="127.0.0.1", host_header="localhost:8080", origin_header="http://localhost:8080")
    assert payload["permission_mode"] == "OWNER_FULL_CONTROL" and "HttpOnly" in cookie
    manager.logout(cookie_header=cookie)
    with pytest.raises(OwnerSessionError, match="missing or expired"):
        manager.require(client_host="127.0.0.1", host_header="localhost:8080", origin_header="http://localhost:8080", cookie_header=cookie)


def test_owner_autonomous_exact_ip_lookup_runs_live_read_without_second_approval():
    runner = _FakeP7Runner()
    broker = ToolBroker(BASE, p7_scoped_available=True, p7_runner=runner)
    engine = ConversationEngine(BASE, tool_broker=broker)
    thread = engine.create_thread(title="Automatic read", permission_mode="OWNER_AUTONOMOUS")
    turn = engine.start_turn(thread["thread_id"], content="what is the ip of tulkarm router", owner_session_digest="a" * 64, run_async=False)
    assert turn["status"] == "COMPLETED" and runner.calls == [{"owner_proceed": True, "binding_id": "p7-router-tulkarm", "target": "10.165.18.2", "check_id": "ip_interface_brief"}]
    answer = engine.store.get_thread(thread["thread_id"])["messages"][-1]["content"]
    assert "10.165.18.2" in answer and "verified now" in answer
    event_types = [event["event_type"] for event in engine.events.list_after(turn["turn_id"])]
    assert "tool.started" in event_types and "tool.completed" in event_types and "tool.approval_required" not in event_types


def test_credential_store_returns_status_not_fragments(tmp_path, monkeypatch):
    monkeypatch.setattr("core.credentials.store.CredentialStore._write_env_reference", lambda self, ref, value: None)
    store = CredentialStore(tmp_path)
    store._keyring = None
    monkeypatch.setenv("P11_TEST_API_KEY", "secret-prefix-and-suffix")
    assert store.get("P11_TEST_API_KEY") == "secret-prefix-and-suffix"
    assert store.status("P11_TEST_API_KEY") == {"credential_ref": "P11_TEST_API_KEY", "status": "CONFIGURED"}
    assert "secret" not in json.dumps(store.status("P11_TEST_API_KEY"))


def test_provider_catalog_and_ssrf_policy():
    registry = ProviderRegistry(BASE)
    profiles = registry.list_profiles()
    assert {item["provider_type"] for item in profiles} == {"codex_app_server", "opencode", "antigravity_cli", "deterministic_local", "ollama", "openai_compatible", "openai", "anthropic"}
    assert all("latest" not in item["model_id"].lower() for item in profiles)
    bad = registry.get("prv_openai_platform", require_enabled=False)
    bad["provider_id"] = "prv_bad_external"
    bad["base_url"] = "http://169.254.169.254/v1"
    with pytest.raises(ProviderRegistryError):
        registry.add_profile(bad)
    bad_local = registry.get("prv_ollama_local", require_enabled=False)
    bad_local["provider_id"] = "prv_bad_local"
    bad_local["base_url"] = "http://10.0.0.5:11434/v1"
    with pytest.raises(ProviderRegistryError):
        registry.add_profile(bad_local)
    bad_userinfo = registry.get("prv_openai_platform", require_enabled=False)
    bad_userinfo["provider_id"] = "prv_bad_userinfo"
    bad_userinfo["base_url"] = "https://user:pass@api.openai.com/v1"
    with pytest.raises(ProviderRegistryError):
        registry.add_profile(bad_userinfo)


def _request(provider_id: str, model_id: str = "reviewed-model") -> ProviderRequest:
    return ProviderRequest(provider_id=provider_id, model_id=model_id, messages=[{"role": "user", "content": "hello"}], tools=[])


def test_deterministic_provider_contract_is_offline():
    profile = ProviderRegistry(BASE).get("prv_local_deterministic")
    events = list(DeterministicLocalProvider(profile).stream(_request(profile["provider_id"], profile["model_id"])))
    assert {event.event_type for event in events} <= CANONICAL_PROVIDER_EVENTS
    assert events[-1].event_type == "completed"
    assert any(event.event_type == "usage" and event.payload["cost_usd"] == 0 for event in events)


def test_openai_responses_contract_uses_store_false_and_normalizes():
    profile = ProviderRegistry(BASE).get("prv_openai_platform", require_enabled=False)
    captured = {}
    def transport(method, url, headers, payload, timeout):
        captured.update(payload)
        yield {"type": "response.output_text.delta", "delta": "hi"}
        yield {"type": "response.completed", "response": {"status": "completed", "usage": {"input_tokens": 1}}}
    adapter = OpenAIProvider(profile, transport=transport)
    events = list(adapter.stream(_request(profile["provider_id"], profile["model_id"]), credential="server-only"))
    assert captured["store"] is False and captured["stream"] is True
    assert [event.event_type for event in events] == ["text_delta", "usage", "completed"]
    assert "server-only" not in json.dumps([event.payload for event in events])


def test_anthropic_and_ollama_normalize_vendor_streams():
    registry = ProviderRegistry(BASE)
    anth = registry.get("prv_anthropic_platform", require_enabled=False)
    def anthropic_transport(*_):
        yield {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "A"}}
        yield {"type": "message_stop"}
    ollama = registry.get("prv_ollama_local", require_enabled=False)
    def ollama_transport(*_):
        yield {"choices": [{"delta": {"content": "O"}, "finish_reason": None}]}
        yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}
    cases = [
        AnthropicProvider(anth, transport=anthropic_transport).stream(_request(anth["provider_id"]), credential="x"),
        OllamaProvider(ollama, transport=ollama_transport).stream(_request(ollama["provider_id"])),
    ]
    for stream in cases:
        events = list(stream)
        assert events[0].event_type == "text_delta" and events[-1].event_type == "completed"


def test_streamed_tool_arguments_are_accumulated_before_proposal():
    registry = ProviderRegistry(BASE)
    openai = registry.get("prv_openai_platform", require_enabled=False)
    def openai_transport(*_):
        yield {"type": "response.output_item.added", "item": {"type": "function_call", "id": "item1", "call_id": "call1", "name": "workspace.status"}}
        yield {"type": "response.function_call_arguments.delta", "item_id": "item1", "delta": "{"}
        yield {"type": "response.function_call_arguments.done", "item_id": "item1", "arguments": "{}"}
        yield {"type": "response.completed", "response": {"status": "completed", "usage": {}}}
    openai_events = list(OpenAIProvider(openai, transport=openai_transport).stream(_request(openai["provider_id"]), credential="x"))
    proposal = next(event for event in openai_events if event.event_type == "tool_proposal")
    assert proposal.payload["name"] == "workspace.status" and proposal.payload["arguments"] == {}

    anth = registry.get("prv_anthropic_platform", require_enabled=False)
    def anthropic_transport(*_):
        yield {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "a1", "name": "workspace.read", "input": {}}}
        yield {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '{"path":"README.md"}'}}
        yield {"type": "content_block_stop", "index": 0}
        yield {"type": "message_stop"}
    anth_events = list(AnthropicProvider(anth, transport=anthropic_transport).stream(_request(anth["provider_id"]), credential="x"))
    proposal = next(event for event in anth_events if event.event_type == "tool_proposal")
    assert proposal.payload["arguments"] == {"path": "README.md"}


def test_provider_switch_does_not_change_permission():
    thread = {"permission_mode": "WORKSPACE_READ", "provider_id": "prv_a"}
    switched = CapabilityPolicy.switch_provider(thread, "prv_b")
    assert switched["permission_mode"] == thread["permission_mode"]


def test_external_authorization_redaction_mismatch_replay_and_expiry():
    clock = [datetime(2026, 8, 20, tzinfo=timezone.utc)]
    manager = ExternalAuthorizationManager(BASE, ttl_seconds=5, now=lambda: clock[0])
    item, sanitized = manager.prepare(thread_id="thr_" + "a" * 20, provider_id="prv_openai_platform", model_id="gpt-5.6-sol", prompt="public question", context={"note": "password=secret"}, evidence_sources=["knowledge/network.md"], data_classification="INTERNAL_REDACTED", includes_live_evidence=False)
    assert "secret" not in json.dumps(sanitized) and "[REDACTED]" in json.dumps(sanitized)
    expected = {field: item[field] for field in ("thread_id", "provider_id", "model_id", "context_digest", "prompt_digest", "redaction_digest")}
    changed = dict(expected, model_id="changed")
    with pytest.raises(ExternalAuthorizationError, match="changed"):
        manager.authorize(item["authorization_id"], expected=changed)
    manager.authorize(item["authorization_id"], expected=expected)
    with pytest.raises(ExternalAuthorizationError, match="replay"):
        manager.authorize(item["authorization_id"], expected=expected)
    second, _ = manager.prepare(thread_id="thr_" + "b" * 20, provider_id="prv_openai_platform", model_id="gpt-5.6-sol", prompt="q", context={}, evidence_sources=["public-doc:test"], data_classification="PUBLIC", includes_live_evidence=False)
    clock[0] += timedelta(seconds=6)
    expected2 = {field: second[field] for field in expected}
    with pytest.raises(ExternalAuthorizationError, match="expired"):
        manager.authorize(second["authorization_id"], expected=expected2)


def test_external_policy_rejects_raw_output_and_unallowlisted_source():
    with pytest.raises(ExternalAuthorizationError):
        ExternalDataPolicy.sanitize({"raw_output": "show running config"})
    with pytest.raises(ExternalAuthorizationError):
        ExternalDataPolicy.validate_sources(["operations/private.log"])
    with pytest.raises(ExternalAuthorizationError):
        ExternalDataPolicy.validate_sources(["knowledge/../../.env"])


def test_conversation_create_resume_search_stream_and_reconnect():
    engine = ConversationEngine(BASE)
    thread = engine.create_thread(title="Firewall question")
    turn = engine.start_turn(thread["thread_id"], content="Explain status", run_async=False)
    assert turn["status"] == "COMPLETED"
    resumed = engine.store.get_thread(thread["thread_id"])
    assert len(resumed["messages"]) == 2 and engine.store.list_threads("Firewall")
    events = engine.events.list_after(turn["turn_id"])
    assert events[0]["event_type"] == "turn.started" and events[-1]["event_type"] == "turn.completed"
    after = engine.events.list_after(turn["turn_id"], events[0]["event_id"])
    assert after[0]["event_id"] == events[1]["event_id"]
    engine.registry.set_enabled("prv_ollama_local", True)
    switched = engine.store.switch_provider(thread["thread_id"], "prv_ollama_local")
    assert switched["permission_mode"] == "OWNER_FULL_CONTROL"
    assert len(engine.store.get_thread(thread["thread_id"])["messages"]) == 2


def test_conversation_evidence_is_truthful_and_unknowns_are_visible():
    engine = ConversationEngine(BASE)
    thread = engine.create_thread(title="evidence truth")
    invalid = {"evidence_id": "fake", "source": "browser", "status": "simulated", "facts": {"health": "up"}}
    turn = engine.start_turn(thread["thread_id"], content="use evidence", evidence=[invalid], run_async=False)
    evidence_event = next(event for event in engine.events.list_after(turn["turn_id"]) if event["event_type"] == "evidence.accepted")
    assert evidence_event["redacted_payload"]["accepted"] is False
    assert evidence_event["redacted_payload"]["count"] == 0 and evidence_event["redacted_payload"]["unknowns"]
    assistant = engine.store.get_thread(thread["thread_id"])["messages"][-1]
    assert assistant["evidence_refs"] == []

    valid = {
        "evidence_id": "ev-live-test", "source": "knowledge/test", "evidence_status": "live_verified", "trust_level": 5,
        "verification_target": "host1", "verification_check_id": "status", "verification_outcome": "success",
        "observed_at": datetime.now(timezone.utc).isoformat(), "facts": {"status": "reachable"},
    }
    second = engine.start_turn(thread["thread_id"], content="use fresh evidence", evidence=[valid], run_async=False)
    accepted_event = next(event for event in engine.events.list_after(second["turn_id"]) if event["event_type"] == "evidence.accepted")
    assert accepted_event["redacted_payload"]["accepted"] is True and accepted_event["redacted_payload"]["count"] == 1


def test_provider_failure_cannot_auto_execute_or_retry_a_tool():
    registry = ProviderRegistry(BASE)
    broker = ToolBroker(BASE)
    class FailingGateway:
        def __init__(self): self.registry = registry
        def stream(self, *_args, **_kwargs):
            yield ProviderEvent("tool_proposal", {"name": "workspace.status", "arguments": {}})
            yield ProviderEvent("failed", {"code": "SIMULATED_PROVIDER_FAILURE"})
    engine = ConversationEngine(BASE, gateway=FailingGateway(), tool_broker=broker)
    thread = engine.create_thread(title="failure isolation", permission_mode="WORKSPACE_READ")
    turn = engine.start_turn(thread["thread_id"], content="propose then fail", run_async=False)
    assert turn["status"] == "FAILED"
    assert len(broker._calls) == 1
    assert next(iter(broker._calls.values()))["status"] == "PROPOSED"
    assert not any(event["event_type"] == "tool.started" for event in engine.events.list_after(turn["turn_id"]))


def test_owner_autonomous_provider_gets_automatic_read_result_and_continues_answering():
    registry = ProviderRegistry(BASE)
    broker = ToolBroker(BASE)
    class TwoRoundGateway:
        def __init__(self): self.registry = registry; self.calls = []
        def stream(self, _provider_id, context, **_kwargs):
            self.calls.append(context)
            if len(self.calls) == 1:
                yield ProviderEvent("tool_proposal", {"name": "workspace.status", "arguments": {}})
            else:
                assert "Automatic read-only tool result" in context[-1]["content"]
                yield ProviderEvent("text_delta", {"text": "Workspace status checked automatically."})
            yield ProviderEvent("completed", {"finish_reason": "stop"})
    gateway = TwoRoundGateway()
    engine = ConversationEngine(BASE, gateway=gateway, tool_broker=broker)
    thread = engine.create_thread(title="automatic tool loop", permission_mode="OWNER_AUTONOMOUS")
    turn = engine.start_turn(thread["thread_id"], content="check the workspace status", owner_session_digest="b" * 64, run_async=False)
    assert turn["status"] == "COMPLETED" and len(gateway.calls) == 2
    assert next(iter(broker._calls.values()))["status"] == "COMPLETED"
    events = engine.events.list_after(turn["turn_id"])
    assert any(event["event_type"] == "tool.proposed" and event["status"] == "AUTOMATIC_READ" for event in events)
    assert any(event["event_type"] == "tool.completed" for event in events)


def test_owner_autonomous_repeated_search_is_bounded_and_forces_an_answer():
    registry = ProviderRegistry(BASE)
    broker = ToolBroker(BASE)
    class RepeatingSearchGateway:
        def __init__(self): self.registry = registry; self.calls = []
        def stream(self, _provider_id, _context, *, tools, **_kwargs):
            self.calls.append([item["name"] for item in tools])
            if tools:
                yield ProviderEvent("tool_proposal", {"name": "workspace.search", "arguments": {"query": "floor 3 policy"}})
                yield ProviderEvent("completed", {"finish_reason": "tool_call"})
                return
            yield ProviderEvent("text_delta", {"text": "No grounded policy ID was found in the collected workspace evidence."})
            yield ProviderEvent("completed", {"finish_reason": "stop"})

    gateway = RepeatingSearchGateway()
    engine = ConversationEngine(BASE, gateway=gateway, tool_broker=broker)
    thread = engine.create_thread(title="bounded repeated search", permission_mode="OWNER_AUTONOMOUS")
    turn = engine.start_turn(thread["thread_id"], content="find the floor 3 policy", owner_session_digest="e" * 64, run_async=False)
    assert turn["status"] == "COMPLETED" and turn.get("failure_code") is None
    assert len(gateway.calls) == 3 and gateway.calls[-1] == []
    assert len(broker._calls) == 2
    answer = engine.store.get_thread(thread["thread_id"])["messages"][-1]["content"]
    assert "No grounded policy ID" in answer


def test_tool_step_limit_has_an_accurate_safe_error_code():
    assert SAFE_PROVIDER_ERRORS["TOOL_STEP_LIMIT_REACHED"][0].startswith("The assistant requested too many tool steps")


def test_owner_autonomous_prepares_exact_write_preview_but_never_applies_it():
    registry = ProviderRegistry(BASE)
    broker = ToolBroker(BASE)
    relative = "docs/p11-autonomous-preview-test.txt"
    target = BASE / relative
    target.unlink(missing_ok=True)
    diff = f"diff --git a/{relative} b/{relative}\nnew file mode 100644\n--- /dev/null\n+++ b/{relative}\n@@ -0,0 +1 @@\n+preview only\n"
    class PreviewGateway:
        def __init__(self): self.registry = registry; self.calls = 0
        def stream(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                yield ProviderEvent("tool_proposal", {"name": "workspace.prepare_patch", "arguments": {"unified_diff": diff}})
            else:
                yield ProviderEvent("text_delta", {"text": "The exact change is ready for owner approval."})
            yield ProviderEvent("completed", {"finish_reason": "stop"})
    engine = ConversationEngine(BASE, gateway=PreviewGateway(), tool_broker=broker)
    thread = engine.create_thread(title="automatic preview", permission_mode="OWNER_AUTONOMOUS")
    turn = engine.start_turn(thread["thread_id"], content="prepare the documented test change", owner_session_digest="c" * 64, run_async=False)
    assert turn["status"] == "COMPLETED" and not target.exists()
    assert len(broker._plans) == 1 and next(iter(broker._plans.values()))["status"] == "PREPARED"
    events = engine.events.list_after(turn["turn_id"])
    assert any(event["event_type"] == "tool.proposed" and event["status"] == "AUTOMATIC_PREPARATION" for event in events)
    assert not any(call["tool_name"] == "workspace.apply_approved_patch" for call in broker._calls.values())


def test_cancellation_token_is_fail_closed():
    token = CancellationToken(60)
    token.cancel()
    with pytest.raises(TurnCancelled):
        token.checkpoint()


def test_turn_timeout_is_bounded(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("core.conversation.cancellation.time.monotonic", lambda: clock[0])
    token = CancellationToken(1)
    clock[0] = 2.0
    with pytest.raises(TurnTimedOut):
        token.checkpoint()


def test_tool_permissions_inventory_and_provider_independence():
    permissions = ToolPermissions(BASE)
    permissions.require("WORKSPACE_READ", "workspace.read")
    with pytest.raises(ToolPermissionError):
        permissions.require("ANSWER_ONLY", "workspace.read")
    broker = ToolBroker(BASE)
    names = {item["tool_name"] for item in broker.registry.list()}
    assert {"workspace.apply_approved_patch", "mne.execute_approved_live_read", "p10.execute"} <= names


def test_workspace_traversal_protected_paths_and_symlink_escape(tmp_path, monkeypatch):
    root = tmp_path / "root"; root.mkdir(); (root / "safe.txt").write_text("ok", encoding="utf-8")
    boundary = WorkspaceBoundary(root, [".env", ".git"])
    assert boundary.resolve("safe.txt").is_file()
    with pytest.raises(WorkspaceBoundaryError): boundary.resolve("../escape.txt")
    with pytest.raises(WorkspaceBoundaryError): boundary.resolve(".env", for_write=True)
    outside = tmp_path / "outside"; outside.mkdir()
    try:
        (root / "link").symlink_to(outside, target_is_directory=True)
    except OSError:
        (root / "link").mkdir()
        original = Path.is_symlink
        monkeypatch.setattr(Path, "is_symlink", lambda self: True if self == root / "link" else original(self))
    with pytest.raises(WorkspaceBoundaryError): boundary.resolve("link/new.txt", for_write=True)


def test_command_policy_rejects_shell_and_argument_injection():
    policy = CommandPolicy(BASE)
    with pytest.raises(CommandPolicyError): policy.run("missing")
    with pytest.raises(CommandPolicyError): policy.run("pytest", ["-c", "whoami"])
    with pytest.raises(CommandPolicyError): policy.run("pytest", ["tests;whoami"])


def test_tool_call_tampering_and_live_read_disable():
    broker = ToolBroker(BASE)
    call = broker.propose(thread_id="thr_" + "a" * 20, turn_id="trn_" + "b" * 20, tool_name="workspace.read", arguments={"path": "README.md"}, permission_mode="WORKSPACE_READ")
    broker._calls[call["tool_call_id"]]["arguments"]["path"] = "AGENTS.md"
    with pytest.raises(ToolBrokerError, match="changed"):
        broker.invoke(call["tool_call_id"])
    with pytest.raises(ToolBrokerError, match="unavailable"):
        broker.prepare_live_read({"binding_id": "p7-switch-tulkarm", "target": "10.165.18.3", "check_id": "ip_interface_brief"})


class _FakeP7Runner:
    def __init__(self, status="SUCCESS"):
        self.status = status
        self.calls = []

    def run_exact(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "status": "COMPLETE",
            "results": [{"binding_id": kwargs["binding_id"], "status": self.status, "connection_attempted": True}],
            "raw_output_included": False,
            "credentials_returned": False,
        }


def test_exact_p7_live_read_requires_phrase_session_and_single_use():
    runner = _FakeP7Runner()
    broker = ToolBroker(BASE, p7_scoped_available=True, p7_runner=runner)
    arguments = broker.live_read_arguments_for_entity("sw-cisco-tulkarm-01")
    assert arguments == {"binding_id": "p7-switch-tulkarm", "target": "10.165.18.3", "check_id": "ip_interface_brief"}
    with pytest.raises(ToolBrokerError, match="canonical"):
        broker.prepare_live_read({**arguments, "target": "172.23.60.2"})
    plan = broker.prepare_live_read(arguments)
    assert plan["status"] == "APPROVAL_REQUIRED" and plan["connection_attempted"] is False
    assert plan["raw_operation_included"] is False and plan["globally_enabled"] is False
    with pytest.raises(ToolBrokerError, match="Exact"):
        broker.approve_live_read(plan["live_read_id"], "PROCEED", owner_session_digest="a" * 64)
    approval = broker.approve_live_read(plan["live_read_id"], plan["approval_phrase"], owner_session_digest="a" * 64)
    with pytest.raises(ToolBrokerError, match="binding changed"):
        broker.execute_live_read(plan["live_read_id"], approval["approval_id"], owner_session_digest="b" * 64)
    result = broker.execute_live_read(plan["live_read_id"], approval["approval_id"], owner_session_digest="a" * 64)
    assert result["status"] == "LIVE_VERIFIED" and result["live_verified"] is True
    assert result["evidence"]["verification_target"] == "10.165.18.3"
    assert result["evidence"]["verification_check_id"] == "ip_interface_brief"
    assert result["evidence"]["trust_level"] == 5 and len(runner.calls) == 1
    with pytest.raises(ToolBrokerError, match="unavailable"):
        broker.execute_live_read(plan["live_read_id"], approval["approval_id"], owner_session_digest="a" * 64)


def test_failed_p7_live_read_never_creates_verified_evidence():
    runner = _FakeP7Runner("CREDENTIAL_NOT_CONFIGURED")
    broker = ToolBroker(BASE, p7_scoped_available=True, p7_runner=runner)
    arguments = broker.live_read_arguments_for_entity("rtr-tulkarm-01")
    assert arguments == {"binding_id": "p7-router-tulkarm", "target": "10.165.18.2", "check_id": "ip_interface_brief"}
    plan = broker.prepare_live_read(arguments)
    approval = broker.approve_live_read(plan["live_read_id"], plan["approval_phrase"], owner_session_digest="c" * 64)
    result = broker.execute_live_read(plan["live_read_id"], approval["approval_id"], owner_session_digest="c" * 64)
    assert result["status"] == "CREDENTIAL_NOT_CONFIGURED"
    assert result["live_verified"] is False and result["evidence"] is None
    assert result["automatic_retry"] is False and len(runner.calls) == 1


def test_live_read_ip_question_prepares_tool_without_provider_or_transport_call():
    registry = ProviderRegistry(BASE)
    class NoProviderGateway:
        def __init__(self): self.registry = registry; self.calls = 0
        def stream(self, *_args, **_kwargs): self.calls += 1; raise AssertionError("provider must not be called"); yield
    runner = _FakeP7Runner()
    gateway = NoProviderGateway()
    broker = ToolBroker(BASE, p7_scoped_available=True, p7_runner=runner)
    engine = ConversationEngine(BASE, gateway=gateway, tool_broker=broker)
    thread = engine.create_thread(title="exact live read", permission_mode="LIVE_READ")
    turn = engine.start_turn(thread["thread_id"], content="what is the ip of tulkarm switch", run_async=False)
    events = engine.events.list_after(turn["turn_id"])
    proposal = next(event for event in events if event["event_type"] == "tool.proposed")
    assert proposal["redacted_payload"]["tool_name"] == "mne.prepare_live_read"
    assert turn["status"] == "COMPLETED" and gateway.calls == 0 and runner.calls == []


def test_workspace_diff_approval_exact_hash_and_replay():
    broker = ToolBroker(BASE)
    diff = "diff --git a/docs/p11-test.txt b/docs/p11-test.txt\nnew file mode 100644\n--- /dev/null\n+++ b/docs/p11-test.txt\n@@ -0,0 +1 @@\n+test\n"
    plan = broker.prepare_patch(diff)
    with pytest.raises(ToolBrokerError): broker.approve_patch(plan["plan_id"], "APPROVE", owner_session_digest="a" * 64)
    approval = broker.approve_patch(plan["plan_id"], plan["approval_phrase"], owner_session_digest="a" * 64)
    assert approval["approved_digest"] == plan["diff_digest"]
    with pytest.raises(ToolBrokerError): broker.approve_patch(plan["plan_id"], plan["approval_phrase"], owner_session_digest="a" * 64)
    symlink_diff = "diff --git a/docs/link b/docs/link\nnew file mode 120000\n--- /dev/null\n+++ b/docs/link\n@@ -0,0 +1 @@\n+../outside\n"
    with pytest.raises(ToolBrokerError, match="symlink"):
        broker.prepare_patch(symlink_diff)


@pytest.fixture
def local_api_server(monkeypatch):
    from core.api import server as api_server
    from core.conversation.engine import ConversationEngine
    test_engine = ConversationEngine(BASE, storage_dir=None)
    monkeypatch.setattr(api_server, "conversation_engine", test_engine)
    password_hash = OwnerCredentialVerifier.hash_password("correct horse battery staple", iterations=300_000, salt=b"p11-owner-test-salt-00001")
    verifier = OwnerCredentialVerifier(username="owner", password_hash=password_hash)
    monkeypatch.setattr(api_server, "owner_credentials", verifier)
    monkeypatch.setattr(api_server, "owner_sessions", OwnerSessionManager(credential_verifier=verifier, max_sessions=1))
    server = BoundedThreadingHTTPServer(("127.0.0.1", 0), MNEBrainAPIHandler, max_workers=8)
    worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
    try:
        yield server.server_port
    finally:
        server.shutdown(); server.server_close(); worker.join(timeout=2)


def _request_http(port, method, path, body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    raw = json.dumps(body).encode() if body is not None else None
    merged = {"Host": f"127.0.0.1:{port}", **(headers or {})}
    if raw is not None: merged["Content-Type"] = "application/json"
    connection.request(method, path, body=raw, headers=merged)
    response = connection.getresponse(); data = response.read(); response_headers = dict(response.getheaders()); connection.close()
    return response.status, response_headers, json.loads(data) if data else {}


def _request_raw(port, method, path, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    connection.request(method, path, headers={"Host": f"127.0.0.1:{port}", **(headers or {})})
    response = connection.getresponse(); data = response.read(); response_headers = dict(response.getheaders()); connection.close()
    return response.status, response_headers, data.decode("utf-8")


def _login_http(port):
    status, headers, session = _request_http(port, "POST", "/api/v2/login", {"username": "owner", "password": "correct horse battery staple"}, {"Origin": f"http://127.0.0.1:{port}"})
    assert status == 200 and "HttpOnly" in headers["Set-Cookie"]
    return headers["Set-Cookie"].split(";", 1)[0], session


def test_api_unauthorized_csrf_replay_and_concurrency(local_api_server):
    port = local_api_server
    status, _, _ = _request_http(port, "POST", "/api/v2/threads", {"title": "x", "request_nonce": "a" * 20})
    assert status == 403
    legacy_status, _, _ = _request_http(port, "GET", "/api/status")
    assert legacy_status == 401
    status, _, _ = _request_http(port, "GET", "/api/v2/session")
    assert status == 401
    cookie, session = _login_http(port)
    legacy_status, _, _ = _request_http(port, "GET", "/api/status", headers={"Cookie": cookie})
    assert legacy_status == 200
    auth = {"Cookie": cookie, "Origin": f"http://127.0.0.1:{port}", "X-CSRF-Token": session["csrf_token"]}
    body = {"title": "API thread", "request_nonce": "b" * 20}
    status, _, thread = _request_http(port, "POST", "/api/v2/threads", body, auth)
    assert status == 201 and thread["permission_mode"] == "OWNER_DIRECT"
    replay, _, _ = _request_http(port, "POST", "/api/v2/threads", body, auth)
    assert replay == 403
    def read_threads(_): return _request_http(port, "GET", "/api/v2/threads", headers={"Cookie": cookie})[0]
    with ThreadPoolExecutor(max_workers=6) as pool:
        assert set(pool.map(read_threads, range(12))) == {200}
    def mixed_request(index):
        if index % 2:
            return _request_http(port, "GET", "/api/v2/threads", headers={"Cookie": cookie})[0]
        concurrent_body = {"title": f"Concurrent {index}", "request_nonce": (f"nonce{index:04d}" * 4)[:20]}
        return _request_http(port, "POST", "/api/v2/threads", concurrent_body, auth)[0]
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert set(pool.map(mixed_request, range(12))) <= {200, 201}
    for index, provider_id in enumerate(("prv_openai_platform", "prv_anthropic_platform", "prv_ollama_local")):
        status, _, result = _request_http(port, "POST", f"/api/v2/providers/{provider_id}/test", {"request_nonce": (f"provider{index}" * 3)[:20]}, auth)
        assert status == 200 and result["status"] == "CONFIG_VALID" and result["network_attempted"] is False and result["secrets_returned"] is False


def test_live_read_http_prepare_approve_execute_is_owner_bound(local_api_server, monkeypatch):
    from core.api import server as api_server
    runner = _FakeP7Runner()
    monkeypatch.setattr(api_server.tool_broker, "_p7_runner", runner)
    port = local_api_server
    cookie, session = _login_http(port)
    auth = {"Cookie": cookie, "Origin": f"http://127.0.0.1:{port}", "X-CSRF-Token": session["csrf_token"]}
    proposal_body = {
        "thread_id": "thr_" + "a" * 20,
        "turn_id": "trn_" + "b" * 20,
        "tool_name": "mne.prepare_live_read",
        "arguments": {"binding_id": "p7-switch-tulkarm", "target": "10.165.18.3", "check_id": "ip_interface_brief"},
        "permission_mode": "LIVE_READ",
        "request_nonce": "live-proposal-nonce-1",
    }
    status, _, call = _request_http(port, "POST", "/api/v2/tool-calls", proposal_body, auth)
    assert status == 201
    status, _, prepared = _request_http(port, "POST", f"/api/v2/tool-calls/{call['tool_call_id']}/invoke", {"request_nonce": "live-invoke-nonce-01"}, auth)
    assert status == 200
    plan = prepared["result"]
    status, _, approval = _request_http(
        port,
        "POST",
        f"/api/v2/live-reads/{plan['live_read_id']}/approve",
        {"approval_phrase": plan["approval_phrase"], "request_nonce": "live-approve-nonce-1"},
        auth,
    )
    assert status == 200
    status, _, result = _request_http(
        port,
        "POST",
        f"/api/v2/live-reads/{plan['live_read_id']}/execute",
        {"approval_id": approval["approval_id"], "request_nonce": "live-execute-nonce-1"},
        auth,
    )
    assert status == 200 and result["status"] == "LIVE_VERIFIED"
    assert result["evidence"]["verification_target"] == "10.165.18.3" and len(runner.calls) == 1


def test_http_sse_last_event_id_reconnect(local_api_server):
    port = local_api_server
    cookie, session = _login_http(port)
    auth = {"Cookie": cookie, "Origin": f"http://127.0.0.1:{port}", "X-CSRF-Token": session["csrf_token"]}
    _, _, thread = _request_http(port, "POST", "/api/v2/threads", {"title": "SSE", "provider_id": "prv_local_deterministic", "request_nonce": "s" * 20}, auth)
    _, _, turn = _request_http(port, "POST", f"/api/v2/threads/{thread['thread_id']}/turns", {"content": "stream", "request_nonce": "t" * 20}, auth)
    time.sleep(0.1)
    status, event_headers, stream = _request_raw(port, "GET", f"/api/v2/turns/{turn['turn_id']}/events", {"Cookie": cookie})
    assert status == 200 and event_headers["Content-Type"] == "text/event-stream"
    assert "event: turn.started" in stream and "event: turn.completed" in stream
    first_id = next(line[4:] for line in stream.splitlines() if line.startswith("id: "))
    _, _, resumed = _request_raw(port, "GET", f"/api/v2/turns/{turn['turn_id']}/events", {"Cookie": cookie, "Last-Event-ID": first_id})
    assert "event: turn.started" not in resumed and "event: turn.completed" in resumed


def test_gui_is_modular_accessible_responsive_and_presentation_only():
    html = (BASE / "gui/index.html").read_text(encoding="utf-8")
    css = (BASE / "gui/styles/main.css").read_text(encoding="utf-8")
    scripts = "\n".join(path.read_text(encoding="utf-8") for path in (BASE / "gui/scripts").glob("*.js"))
    assert 'class="skip-link"' in html and 'aria-live="polite"' in html and '<label for="composer-input">' in html
    assert '@media(max-width:680px)' in css and ':focus-visible' in css
    assert "innerHTML" not in scripts and "expected_approval_phrase" not in scripts
    assert "risk_level" in scripts and "rollback_bundle" in scripts and "approval_phrase" in scripts
    assert "textContent" in scripts and "type=\"module\"" in html


def test_server_source_has_no_wildcard_cors_oauth_listener_or_plaintext_key_json():
    source = (BASE / "core/api/server.py").read_text(encoding="utf-8")
    assert "Access-Control-Allow-Origin" not in source
    assert "api_keys_storage.json" not in source
    assert "port 1455" not in source and "start_oauth_port_1455" not in source
    assert 'bind_host = host or str(security_policy.get("bind_host", "127.0.0.1"))' in source
    assert "BoundedThreadingHTTPServer" in source
