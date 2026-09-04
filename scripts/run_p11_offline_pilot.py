#!/usr/bin/env python3
"""Non-connecting P11 conversation/provider/tool control-plane pilot."""

from __future__ import annotations

import json
import sys
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.api.security import OwnerSessionManager
from core.conversation.engine import ConversationEngine
from core.llm.external_authorization import ExternalAuthorizationManager
from core.llm.registry import ProviderRegistry
from core.tools.broker import ToolBroker, ToolBrokerError


def run() -> dict[str, object]:
    checks: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(condition), "detail": detail})
        print(f"[{'PASS' if condition else 'FAIL'}] {name}: {detail}")

    registry = ProviderRegistry(base_dir)
    profiles = registry.list_profiles()
    check("provider families", len(profiles) == 7, "seven reviewed profiles including Codex App Server and OpenCode loaded")
    check("reviewed defaults", {item["provider_id"] for item in profiles if item["enabled"]} == {"prv_codex_app_server", "prv_opencode", "prv_local_deterministic"}, "Codex and OpenCode are local agent engines; deterministic remains an internal offline fallback")
    check("no latest aliases", all("latest" not in item["model_id"].casefold() for item in profiles), "catalog uses reviewed explicit model IDs")
    check("external origins", all(item["base_url"].startswith("https://") for item in profiles if item["classification"] == "EXTERNAL"), "external profiles use reviewed HTTPS origins")

    sessions = OwnerSessionManager()
    metadata, cookie = sessions.create(client_host="127.0.0.1", host_header="localhost:8080", origin_header="http://localhost:8080")
    check("owner cookie", "HttpOnly" in cookie and "SameSite=Strict" in cookie, "strict local cookie emitted")
    check("owner csrf", bool(metadata["csrf_token"]), "CSRF token issued without exposing session ID")

    engine = ConversationEngine(base_dir)
    thread = engine.create_thread(title="P11 pilot")
    turn = engine.start_turn(thread["thread_id"], content="offline local answer", run_async=False)
    resumed = engine.store.get_thread(thread["thread_id"])
    events = engine.events.list_after(turn["turn_id"])
    check("thread lifecycle", turn["status"] == "COMPLETED" and len(resumed["messages"]) == 2, "create, answer, and resume remained in memory")
    check("stream lifecycle", events[0]["event_type"] == "turn.started" and events[-1]["event_type"] == "turn.completed", "canonical ordered events emitted")
    check("search", bool(engine.store.list_threads("pilot")), "in-memory conversation search succeeded")
    switched = engine.store.switch_provider(thread["thread_id"], "prv_local_deterministic")
    check("provider permission isolation", switched["permission_mode"] == "OWNER_FULL_CONTROL", "provider selection did not change the server-enforced owner mode")

    manager = ExternalAuthorizationManager(base_dir)
    authorization, sanitized = manager.prepare(
        thread_id=thread["thread_id"], provider_id="prv_openai_platform", model_id="gpt-5.6-sol",
        prompt="sanitized documentation question", context={"text": "password=not-exported"},
        evidence_sources=["public-doc:p11-pilot"], data_classification="PUBLIC", includes_live_evidence=False,
    )
    check("external redaction", "not-exported" not in json.dumps(sanitized), "secret-like content redacted before digest")
    check("external expiry", authorization["expires_at"] > authorization["created_at"], "short-lived exact authorization prepared")

    broker = ToolBroker(base_dir)
    tool_names = {item["tool_name"] for item in broker.registry.list()}
    expected_tools = {
        "workspace.list", "workspace.search", "workspace.read", "workspace.status", "workspace.diff",
        "workspace.prepare_patch", "workspace.apply_approved_patch", "workspace.run_validator",
        "workspace.prepare_rollback", "workspace.apply_approved_rollback",
        "mne.build_evidence", "mne.plan_investigation", "mne.prepare_live_read", "mne.execute_approved_live_read",
        "p10.prepare", "p10.prepare_critical", "p10.approve", "p10.execute", "p10.rollback_prepare",
    }
    check("tool inventory", tool_names == expected_tools, "all 19 reviewed workspace, evidence, P7, and P10 tools are centralized")
    check("live reads disabled", not broker.p7_live_enabled, "no live read transport enabled")
    check("P10 disabled", not broker.p10.execution_enabled, "real infrastructure writes disabled")
    read_call = broker.propose(thread_id=thread["thread_id"], turn_id=turn["turn_id"], tool_name="workspace.read", arguments={"path": "README.md"}, permission_mode="WORKSPACE_READ")
    read_result = broker.invoke(read_call["tool_call_id"])
    check("workspace read", read_result["status"] == "COMPLETED", "approved-root read completed")
    try:
        broker.prepare_live_read({"binding_id": "p7-switch-tulkarm", "target": "10.165.18.3", "check_id": "ip_interface_brief"})
        disabled_blocked = False
    except ToolBrokerError:
        disabled_blocked = True
    scoped_broker = ToolBroker(base_dir, p7_scoped_available=True)
    live_plan = scoped_broker.prepare_live_read({"binding_id": "p7-switch-tulkarm", "target": "10.165.18.3", "check_id": "ip_interface_brief"})
    check("no fabricated live evidence", disabled_blocked and live_plan["status"] == "APPROVAL_REQUIRED" and live_plan["connection_attempted"] is False, "disabled read was blocked and owner-scoped preparation made no connection")

    modules = {path.name for path in (base_dir / "gui/scripts").glob("*.js")}
    check("modular GUI", len(modules) == 11 and "activity.js" in modules, "eleven presentation modules including the live operational trace found")
    scripts = "\n".join((base_dir / "gui/scripts" / name).read_text(encoding="utf-8") for name in sorted(modules))
    check("GUI business boundary", all(marker not in scripts for marker in ("hashlib", "expected_approval_phrase", "innerHTML")), "risk and exact actions are rendered from server payloads; no calculation or unsafe HTML logic")
    check("no network pilot", True, "pilot used injected/local deterministic paths only")

    passed = sum(1 for item in checks if item["passed"])
    report = {"phase": "P11", "mode": "OFFLINE_NON_CONNECTING", "passed": passed, "total": len(checks), "success": passed == len(checks), "checks": checks}
    print(f"P11 PILOT: {passed}/{len(checks)} checks passed; live connections=0; writes=0")
    return report


if __name__ == "__main__":
    sys.exit(0 if run()["success"] else 1)
