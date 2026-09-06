"""Offline acceptance tests for the governed OpenCode secondary engine."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from core.conversation.thread_store import ThreadStore
from core.opencode.custom_providers import CustomProviderError, CustomProviderStore, validate_endpoint
from core.opencode.runtime import GovernedToolBridge, OpenCodeRuntime


BASE = Path(__file__).resolve().parent.parent


def _model(*, paid: bool = False) -> dict:
    return {
        "id": "temporary-free-model",
        "providerID": "sample",
        "name": "Temporary Free Model",
        "status": "active",
        "cost": {"input": 1 if paid else 0, "output": 0, "cache": {"read": 0, "write": 0}},
        "limit": {"context": 128000, "output": 8192},
        "capabilities": {"toolcall": True, "reasoning": True},
    }


class FakeClient:
    def __init__(self):
        self.calls = []
        self.connected = ["sample"]

    def request(self, method, path, payload=None, timeout=0):
        self.calls.append((method, path, payload))
        if path.startswith("/provider/auth"):
            return {"sample": [{"type": "api", "label": "API key"}, {"type": "oauth", "label": "Device login", "prompts": [{"key": "organization", "type": "select", "message": "Organization", "options": [{"value": "default", "label": "Default"}]}]}]}
        if path.startswith("/provider") and method == "GET":
            return {"all": [{"id": "sample", "name": "Sample", "source": "api", "env": ["SAMPLE_API_KEY"], "options": {}, "models": {"temporary-free-model": _model()}}], "default": {}, "connected": list(self.connected)}
        if path.startswith("/session/status"):
            return {"ses_test": {"type": "idle"}}
        if path.startswith("/session/ses_test/message") and method == "GET":
            return [{"info": {"role": "assistant"}, "parts": [{"type": "reasoning", "text": "private"}, {"type": "text", "text": "safe final answer"}]}]
        if path.startswith("/session") and method == "POST" and "/prompt_async" not in path and "/abort" not in path:
            return {"id": "ses_test"}
        if path.startswith("/auth/") and method == "PUT":
            return True
        if path.startswith("/auth/") and method == "DELETE":
            self.connected = []
            return True
        return None

    def events(self, path, timeout=0):
        yield {"type": "message.part.delta", "properties": {"sessionID": "ses_test", "field": "text", "delta": "safe final answer"}}
        yield {"type": "session.idle", "properties": {"sessionID": "ses_test"}}


class DummyBroker:
    def __init__(self):
        self.proposals = []

    def propose(self, **kwargs):
        self.proposals.append(kwargs)
        return {"tool_call_id": "tcall_1234567890123456", "argument_digest": "a" * 64}

    def invoke(self, tool_call_id, owner_session_digest=None):
        return {"tool_call_id": tool_call_id, "status": "COMPLETED", "result": {"status": "CLEAN"}}


class DummyBridge:
    def __init__(self): self.active = None
    def bind(self, state): self.active = state
    def unbind(self, turn_id): self.active = None


def _runtime(client=None, broker=None, events=None, completed=None, failed=None):
    return OpenCodeRuntime(
        BASE,
        tool_broker=broker or DummyBroker(),
        event_sink=lambda *event: (events if events is not None else []).append(event),
        completion_sink=lambda *event: (completed if completed is not None else []).append(event),
        failure_sink=lambda *event: (failed if failed is not None else []).append(event),
        client=client or FakeClient(),
    )


def test_dynamic_catalog_preserves_reported_models_costs_auth_and_warnings():
    client = FakeClient()
    runtime = _runtime(client)
    catalog = runtime.refresh_catalog(start_process=False)
    assert runtime.readiness()["status"] == "READY"
    assert catalog["models"][0]["selection_id"] == "sample/temporary-free-model"
    assert catalog["models"][0]["cost_classification"] == "FREE"
    assert catalog["models"][0]["tool_support"] and catalog["models"][0]["reasoning"]
    assert catalog["providers"][0]["authentication_methods"] == [
        {"index": 0, "type": "api", "label": "API key", "prompts": []},
        {"index": 1, "type": "oauth", "label": "Device login", "prompts": [{"key": "organization", "type": "select", "message": "Organization", "required": True, "options": [{"value": "default", "label": "Default"}]}]},
    ]
    assert catalog["secrets_returned"] is False and "options" not in catalog["providers"][0]
    assert OpenCodeRuntime._cost_classification({"input": 0}) == "UNKNOWN"
    assert OpenCodeRuntime._cost_classification({"input": 0, "output": 0}) == "FREE"
    assert OpenCodeRuntime._cost_classification({"input": 0, "output": 0.01}) == "PAID"


def test_open_code_turn_uses_explicit_model_denies_native_tools_and_hides_reasoning():
    client = FakeClient(); events = []; completed = []; failed = []
    runtime = _runtime(client, events=events, completed=completed, failed=failed)
    runtime._bridge = DummyBridge()
    runtime.refresh_catalog(start_process=False)
    runtime.start_turn(
        gui_thread_id="thr_1234567890123456", gui_turn_id="trn_1234567890123456",
        content="investigate safely", owner_session_digest="a" * 64,
        model_id="sample/temporary-free-model", permission_mode="OWNER_AUTONOMOUS", timeout_seconds=5,
    )
    for _ in range(200):
        if completed or failed: break
        time.sleep(.01)
    assert not failed and completed[-1][-1] == "safe final answer"
    prompt = next(payload for method, path, payload in client.calls if method == "POST" and "/prompt_async" in path)
    assert prompt["model"] == {"providerID": "sample", "modelID": "temporary-free-model"}
    assert all(value is False for value in prompt["tools"].values())
    assert "private" not in json.dumps(events + completed)
    assert any(event[2] == "answer.final" for event in events)


def test_api_key_is_forwarded_only_to_opencode_and_never_returned():
    client = FakeClient(); runtime = _runtime(client); runtime.refresh_catalog(start_process=False)
    credential_sample = "not-returned-provider-key"
    result = runtime.connect_api_key("sample", credential_sample)
    auth_call = next(call for call in client.calls if call[0] == "PUT")
    assert auth_call[2] == {"type": "api", "key": credential_sample}
    assert credential_sample not in json.dumps(result) and result["secrets_returned"] is False


def test_opencode_child_environment_excludes_mne_device_credentials(monkeypatch):
    monkeypatch.setenv("MNE_FORTIGATE_PASSWORD", "device-value")
    monkeypatch.setenv("AI_SAMPLE_API_KEY", "provider-value")
    monkeypatch.setenv("OPENCODE_PROVIDER_ENV_REFS", "AI_SAMPLE_API_KEY")
    environment = _runtime()._child_environment()
    assert "MNE_FORTIGATE_PASSWORD" not in environment
    assert environment["AI_SAMPLE_API_KEY"] == "provider-value"


def test_governed_mcp_bridge_routes_only_allowlisted_broker_calls():
    broker = DummyBroker(); events = []; runtime = _runtime(broker=broker, events=events)
    bridge = GovernedToolBridge(runtime)
    try:
        bridge.bind({"gui_thread_id": "thr_1234567890123456", "gui_turn_id": "trn_1234567890123456", "owner_session_digest": "b" * 64, "permission_mode": "OWNER_AUTONOMOUS"})
        result = bridge.run("workspace_status", {})
        assert result["status"] == "COMPLETED" and broker.proposals[0]["tool_name"] == "workspace.status"
        with pytest.raises(Exception, match="outside"):
            bridge.run("shell", {"command": "whoami"})
    finally:
        bridge.stop()


def test_custom_provider_validation_blocks_ssrf_credentials_and_sensitive_headers(tmp_path):
    validate_endpoint("http://127.0.0.1:11434/v1", allow_loopback=True)
    with pytest.raises(CustomProviderError): validate_endpoint("http://169.254.169.254/latest", allow_loopback=True)
    with pytest.raises(CustomProviderError): validate_endpoint("https://user:pass@example.com/v1")
    with pytest.raises(CustomProviderError): validate_endpoint("file:///etc/passwd")
    (tmp_path / "config").mkdir()
    store = CustomProviderStore(tmp_path)
    profile = {"provider_id": "local_test", "display_name": "Local Test", "base_url": "http://127.0.0.1:11434/v1", "protocol": "chat_completions", "models": [{"model_id": "model-1", "display_name": "Model 1"}], "environment_ref": "LOCAL_TEST_KEY", "headers": {"X-Tenant": "safe"}, "allow_loopback": True}
    saved = store.upsert(profile)
    assert saved["environment_ref"] == "LOCAL_TEST_KEY" and "api_key" not in json.dumps(saved).casefold()
    profile["headers"] = {"Authorization": "Bearer secret"}
    with pytest.raises(CustomProviderError): store.upsert(profile)


def test_gemini_v1_import_migrates_future_engine_without_rewriting_history():
    store = ThreadStore(BASE)
    payload = {
        "format": "MNE_BRAIN_CONVERSATION_V1", "exported_at": "2026-08-31T00:00:00+00:00",
        "thread": {"title": "Historical", "provider_id": "prv_gemini_cli", "engine_id": "gemini", "model_id": "auto", "permission_mode": "OWNER_AUTONOMOUS"},
        "turns": [{"status": "COMPLETED", "messages": [{"role": "user", "content": "hello", "evidence_refs": []}, {"role": "assistant", "content": "historical answer", "evidence_refs": []}]}],
        "contains_credentials": False, "contains_server_diagnostics": False,
    }
    imported = store.import_thread(payload)
    assert imported["engine_id"] == "opencode" and imported["provider_id"] == "prv_opencode" and imported["model_id"] == "select-model"
    assert imported["turns"][0]["engine_id"] == "gemini" and imported["turns"][0]["provider_id"] == "prv_gemini_cli"
    assert [message["content"] for message in imported["messages"]] == ["hello", "historical answer"]
    exported = store.export_thread(imported["thread_id"])
    assert exported["format"] == "MNE_BRAIN_CONVERSATION_V2" and exported["turns"][0]["engine_id"] == "gemini"


def test_gui_exposes_only_codex_and_opencode_with_safe_recovery():
    html = (BASE / "gui/index.html").read_text(encoding="utf-8")
    scripts = "\n".join(path.read_text(encoding="utf-8") for path in (BASE / "gui/scripts").glob("*.js"))
    assert "OpenCode providers" in html and "opencode-api-key" in html and "custom-provider-protocol" in html
    assert "Retry with another OpenCode model" in scripts and "Retry with Codex" in scripts
    assert "innerHTML" not in scripts and "localStorage" in scripts
    assert "GEMINI_API_KEY" not in html and "Gemini CLI" not in html


def test_opencode_detects_payment_error_and_fails_immediately():
    class ErrorClient(FakeClient):
        def events(self, path, timeout=0):
            yield {
                "type": "message.updated",
                "properties": {
                    "info": {
                        "sessionID": "ses_test",
                        "role": "assistant",
                        "error": {
                            "name": "APIError",
                            "data": {
                                "message": "No payment method. Add a payment method here: https://opencode.ai/billing",
                                "statusCode": 401,
                            },
                        },
                    },
                },
            }

        def request(self, method, path, payload=None, timeout=0):
            if path.startswith("/session/ses_test/message") and method == "GET":
                return [{
                    "info": {
                        "role": "assistant",
                        "error": {"data": {"message": "No payment method"}},
                    },
                    "parts": [],
                }]
            return super().request(method, path, payload, timeout)

    client = ErrorClient()
    failed = []
    runtime = _runtime(client, failed=failed)
    runtime._bridge = DummyBridge()
    runtime.refresh_catalog(start_process=False)
    runtime.start_turn(
        gui_thread_id="thr_1234567890123456",
        gui_turn_id="trn_1234567890123456",
        content="check policies",
        owner_session_digest="a" * 64,
        model_id="sample/temporary-free-model",
        permission_mode="OWNER_AUTONOMOUS",
        timeout_seconds=5,
    )
    for _ in range(100):
        if failed:
            break
        time.sleep(0.01)
    assert failed == [("trn_1234567890123456", "OPENCODE_PAYMENT_REQUIRED")]


def test_opencode_completes_from_terminal_message_without_session_idle():
    class NoIdleClient(FakeClient):
        def events(self, path, timeout=0):
            yield {"type": "message.part.delta", "properties": {"sessionID": "ses_test", "field": "text", "delta": "fast answer"}}

        def request(self, method, path, payload=None, timeout=0):
            if path.startswith("/session/status"):
                return {}
            if path.startswith("/session/ses_test/message") and method == "GET":
                return [{
                    "info": {
                        "role": "assistant",
                        "time": {"created": 1000, "completed": 2000},
                    },
                    "parts": [{"type": "text", "text": "fast answer"}],
                }]
            return super().request(method, path, payload, timeout)

    client = NoIdleClient()
    completed = []
    runtime = _runtime(client, completed=completed)
    runtime._bridge = DummyBridge()
    runtime.refresh_catalog(start_process=False)
    runtime.start_turn(
        gui_thread_id="thr_1234567890123456",
        gui_turn_id="trn_1234567890123456",
        content="check policies",
        owner_session_digest="a" * 64,
        model_id="sample/temporary-free-model",
        permission_mode="OWNER_AUTONOMOUS",
        timeout_seconds=5,
    )
    for _ in range(100):
        if completed:
            break
        time.sleep(0.01)
    assert completed and completed[-1][-1] == "fast answer"
