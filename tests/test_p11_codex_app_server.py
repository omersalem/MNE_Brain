"""Security and protocol tests for the Codex App Server GUI harness."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.codex.app_server import CodexAppServerError, CodexAppServerHarness, SanitizedWorkspace, discover_repository_root


class _FakeBroker:
    def __init__(self):
        self.calls = []

    def prepare_patch(self, diff):
        self.calls.append(("prepare", diff))
        return {"plan_id": "wplan_1234567890123456", "approval_phrase": "SERVER PHRASE"}

    def approve_patch(self, plan_id, phrase, *, owner_session_digest):
        self.calls.append(("approve", plan_id, phrase, owner_session_digest))
        return {"approval_id": "wappr_1234567890123456"}

    def apply_approved_patch(self, plan_id, approval_id, *, owner_session_digest):
        self.calls.append(("apply", plan_id, approval_id, owner_session_digest))
        return {"status": "APPLIED", "rollback_available": True}


class _FakeRpc:
    def __init__(self):
        self.responses = []
        self.initialized = True
        self.process = SimpleNamespace(poll=lambda: None)

    def respond(self, request_id, *, result=None, error=None):
        self.responses.append((request_id, result, error))


def _git_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)
    return path


def _harness(repo: Path):
    events = []
    harness = CodexAppServerHarness(
        repo,
        tool_broker=_FakeBroker(),
        event_sink=lambda thread, turn, event, payload: events.append((thread, turn, event, payload)),
        completion_sink=lambda *_: None,
        failure_sink=lambda *_: None,
    )
    harness._rpc = _FakeRpc()
    return harness, events


def test_repository_discovery_supports_main_checkout_and_worktree_marker(tmp_path):
    repo = _git_repo(tmp_path / "main")
    nested = repo / "core" / "module"
    nested.mkdir(parents=True)
    assert discover_repository_root(nested) == repo.resolve()

    linked = tmp_path / "linked"
    linked.mkdir()
    (linked / ".git").write_text("gitdir: ../main/.git/worktrees/linked\n", encoding="utf-8")
    assert discover_repository_root(linked) == linked.resolve()


def test_sanitized_workspace_excludes_credentials_vcs_and_symlinks(tmp_path):
    repo = _git_repo(tmp_path / "repo")
    (repo / "README.md").write_text("safe\n", encoding="utf-8")
    (repo / ".env").write_text("MNE_SECRET=never-copy\n", encoding="utf-8")
    (repo / ".env.example").write_text("MNE_SECRET=reference-only\n", encoding="utf-8")
    try:
        (repo / "outside-link").symlink_to(tmp_path / "outside")
    except OSError:
        pass
    workspace = SanitizedWorkspace(repo, "thr_1234567890123456")
    assert (workspace.root / "README.md").read_text(encoding="utf-8") == "safe\n"
    assert not (workspace.root / ".env").exists()
    assert (workspace.root / ".env.example").exists()
    assert not (workspace.root / ".git").exists()
    assert not (workspace.root / "outside-link").exists()
    assert workspace.relative_real_path(str(workspace.root / "README.md")) == "README.md"
    with pytest.raises(CodexAppServerError, match="outside"):
        workspace.relative_real_path(str(repo / "README.md"))


def test_sanitized_workspace_cleanup_is_limited_to_its_validated_temp_root(tmp_path):
    repo = _git_repo(tmp_path / "repo")
    (repo / "README.md").write_text("safe\n", encoding="utf-8")
    workspace = SanitizedWorkspace(repo, "thr_cleanup")
    mirror = workspace.root
    assert mirror.exists() and mirror.parent == Path(tempfile.gettempdir()).resolve()
    workspace.cleanup()
    assert not mirror.exists()

    workspace.root = repo
    with pytest.raises(CodexAppServerError, match="unrecognized"):
        workspace.cleanup()


def test_child_environment_is_allowlisted_and_never_inherits_api_or_device_secrets(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "never-inherit")
    monkeypatch.setenv("MNE_FORTIGATE_PASSWORD", "never-inherit")
    monkeypatch.setenv("UNRELATED_SECRET", "never-inherit")
    monkeypatch.setenv("PATH", os.environ.get("PATH", ""))
    child = CodexAppServerHarness._child_environment()
    assert child["MNE_BRAIN_CODEX_CHILD"] == "1"
    assert "OPENAI_API_KEY" not in child
    assert "MNE_FORTIGATE_PASSWORD" not in child
    assert "UNRELATED_SECRET" not in child
    assert "PATH" in {key.upper() for key in child}


def test_responses_dynamic_tool_aliases_are_valid_and_map_only_to_governed_tools():
    aliases = CodexAppServerHarness._DYNAMIC_TOOLS
    assert aliases
    assert all(re.fullmatch(r"[A-Za-z0-9_-]+", alias) for alias in aliases)
    assert set(aliases.values()) == {
        "mne.build_evidence", "mne.plan_investigation", "mne.prepare_live_read",
        "owner_direct.discover", "owner_direct.identity_audit", "owner_direct.prepare_write",
        "p10.prepare", "p10.prepare_critical",
    }


def test_codex_developer_instructions_match_owner_direct_dynamic_tools():
    instructions = CodexAppServerHarness._developer_instructions()
    assert "owner_direct_discover" in instructions
    assert "owner_direct_identity_audit" in instructions
    assert "owner_direct_prepare_write" in instructions
    assert "UI alone performs final write confirmation" in instructions


def test_safe_shadow_read_is_automatic_but_direct_infrastructure_command_is_declined(tmp_path):
    repo = _git_repo(tmp_path / "repo")
    (repo / "README.md").write_text("safe\n", encoding="utf-8")
    harness, events = _harness(repo)
    workspace = SanitizedWorkspace(repo, "thr_1234567890123456")
    harness._threads["thr_1234567890123456"] = {"workspace": workspace, "codex_thread_id": "cth_1"}
    state = {
        "gui_thread_id": "thr_1234567890123456", "gui_turn_id": "trn_1234567890123456",
        "owner_session_digest": "a" * 64,
    }
    harness._turns_by_codex["ctr_1"] = state

    safe_item = {
        "id": "item_safe", "cwd": str(workspace.root),
        "command": "pwsh -Command Get-Content README.md",
        "commandActions": [{"command": "Get-Content -LiteralPath .\\README.md -TotalCount 1"}],
    }
    harness._items["item_safe"] = safe_item
    harness._prepare_approval("rpc_safe", "item/commandExecution/requestApproval", {"turnId": "ctr_1", "itemId": "item_safe"})
    assert harness._rpc.responses[-1][1] == {"decision": "accept"}
    assert events[-1][2] == "tool.proposed" and events[-1][3]["status"] == "AUTOMATIC_READ"

    safe_item["id"] = "item_pipeline"
    safe_item["commandActions"] = [{"command": "Get-Content -LiteralPath .\\README.md | Where-Object { $_ -match '^#' } | Select-Object -First 1"}]
    harness._items["item_pipeline"] = safe_item
    harness._prepare_approval("rpc_pipeline", "item/commandExecution/requestApproval", {"turnId": "ctr_1", "itemId": "item_pipeline"})
    assert harness._rpc.responses[-1][1] == {"decision": "accept"}

    blocked_item = {
        "id": "item_blocked", "cwd": str(workspace.root),
        "command": "ssh admin@10.0.0.1 show system",
        "commandActions": [{"command": "ssh admin@10.0.0.1 show system"}],
    }
    harness._items["item_blocked"] = blocked_item
    harness._prepare_approval("rpc_blocked", "item/commandExecution/requestApproval", {"turnId": "ctr_1", "itemId": "item_blocked"})
    assert harness._rpc.responses[-1][1] == {"decision": "decline"}
    assert events[-1][2] == "tool.completed" and events[-1][3]["status"] == "POLICY_BLOCKED"
    assert not harness._approvals


def test_safe_reads_from_exact_skill_memory_and_attachment_roots_need_no_click(tmp_path, monkeypatch):
    repo = _git_repo(tmp_path / "repo")
    (repo / "README.md").write_text("safe\n", encoding="utf-8")
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    for name in ("SKILL.md", "MEMORY.md", "request.txt"):
        (trusted / name).write_text("owner-visible reference\n", encoding="utf-8")
    (trusted / ".env").write_text("never-read\n", encoding="utf-8")
    monkeypatch.setattr(CodexAppServerHarness, "_trusted_read_roots", staticmethod(lambda: (trusted.resolve(),)))

    harness, events = _harness(repo)
    workspace = SanitizedWorkspace(repo, "thr_1234567890123456")
    harness._threads["thr_1234567890123456"] = {"workspace": workspace, "codex_thread_id": "cth_1"}
    harness._turns_by_codex["ctr_1"] = {
        "gui_thread_id": "thr_1234567890123456", "gui_turn_id": "trn_1234567890123456",
        "owner_session_digest": "c" * 64,
    }

    for index, name in enumerate(("SKILL.md", "MEMORY.md", "request.txt")):
        item_id = f"item_trusted_{index}"
        harness._items[item_id] = {
            "id": item_id, "cwd": str(workspace.root),
            "commandActions": [{"command": f"Get-Content -LiteralPath '{trusted / name}'"}],
        }
        harness._prepare_approval(
            f"rpc_trusted_{index}", "item/commandExecution/requestApproval",
            {"turnId": "ctr_1", "itemId": item_id},
        )
        assert harness._rpc.responses[-1][1] == {"decision": "accept"}
        assert events[-1][2] == "tool.proposed" and events[-1][3]["status"] == "AUTOMATIC_READ"

    protected_id = "item_protected"
    harness._items[protected_id] = {
        "id": protected_id, "cwd": str(workspace.root),
        "commandActions": [{"command": f"Get-Content -LiteralPath '{trusted / '.env'}'"}],
    }
    response_count = len(harness._rpc.responses)
    harness._prepare_approval(
        "rpc_protected", "item/commandExecution/requestApproval",
        {"turnId": "ctr_1", "itemId": protected_id},
    )
    assert len(harness._rpc.responses) == response_count
    assert events[-1][2] == "tool.approval_required"


def test_external_paths_outside_trusted_read_roots_are_not_automatically_approved(tmp_path, monkeypatch):
    repo = _git_repo(tmp_path / "repo")
    workspace = SanitizedWorkspace(repo, "thr_external")
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    monkeypatch.setattr(CodexAppServerHarness, "_trusted_read_roots", staticmethod(lambda: (trusted.resolve(),)))

    item = {
        "cwd": str(workspace.root),
        "commandActions": [{"command": f"Get-Content -LiteralPath '{outside}'"}],
    }
    assert CodexAppServerHarness._is_safe_shadow_command(item, workspace) is False


def test_completed_agent_message_is_authoritative_and_published_before_turn_completion(tmp_path):
    repo = _git_repo(tmp_path / "repo")
    events = []
    completions = []
    failures = []
    harness = CodexAppServerHarness(
        repo,
        tool_broker=_FakeBroker(),
        event_sink=lambda thread, turn, event, payload: events.append((thread, turn, event, payload)),
        completion_sink=lambda thread, turn, answer: completions.append((thread, turn, answer)),
        failure_sink=lambda turn, code: failures.append((turn, code)),
    )
    harness._turns_by_codex["ctr_1"] = {
        "gui_thread_id": "thr_1", "gui_turn_id": "trn_1", "final_text": ["partial"],
        "progress_text": [], "authoritative_final_text": "", "active": True,
    }
    harness._items["msg_1"] = {"id": "msg_1", "type": "agentMessage", "phase": "final_answer"}

    harness._on_notification("item/completed", {
        "turnId": "ctr_1",
        "item": {"id": "msg_1", "type": "agentMessage", "phase": "final_answer", "text": "Complete answer."},
    })
    harness._on_notification("turn/completed", {"turn": {"id": "ctr_1", "status": "completed", "items": []}})

    assert failures == []
    assert completions == [("thr_1", "trn_1", "Complete answer.")]
    assert events[-1][2:] == ("answer.final", {"text": "Complete answer.", "phase": "final_answer"})


def test_completed_codex_turn_without_final_answer_fails_instead_of_ending_silently(tmp_path):
    repo = _git_repo(tmp_path / "repo")
    completions = []
    failures = []
    harness = CodexAppServerHarness(
        repo,
        tool_broker=_FakeBroker(),
        event_sink=lambda *_: None,
        completion_sink=lambda *args: completions.append(args),
        failure_sink=lambda turn, code: failures.append((turn, code)),
    )
    harness._turns_by_codex["ctr_empty"] = {
        "gui_thread_id": "thr_1", "gui_turn_id": "trn_empty", "final_text": [],
        "progress_text": [], "authoritative_final_text": "", "active": True,
    }

    harness._on_notification("turn/completed", {"turn": {"id": "ctr_empty", "status": "completed", "items": []}})

    assert completions == []
    assert failures == [("trn_empty", "CODEX_EMPTY_RESPONSE")]


def test_file_change_requires_exact_single_use_approval_and_exposes_rollback(tmp_path):
    repo = _git_repo(tmp_path / "repo")
    (repo / "note.txt").write_text("alpha\nbeta\n", encoding="utf-8")
    harness, events = _harness(repo)
    workspace = SanitizedWorkspace(repo, "thr_1234567890123456")
    harness._threads["thr_1234567890123456"] = {"workspace": workspace, "codex_thread_id": "cth_1"}
    harness._turns_by_codex["ctr_1"] = {
        "gui_thread_id": "thr_1234567890123456", "gui_turn_id": "trn_1234567890123456",
        "owner_session_digest": "b" * 64,
    }
    harness._items["file_1"] = {
        "id": "file_1", "changes": [{
            "path": str(workspace.root / "note.txt"), "kind": {"type": "update"},
            "diff": "@@ -1,2 +1,2 @@\n alpha\n-beta\n+gamma\n",
        }],
    }
    harness._prepare_approval("rpc_file", "item/fileChange/requestApproval", {"turnId": "ctr_1", "itemId": "file_1"})
    proposal = events[-1][3]
    assert proposal["kind"] == "FILE_CHANGE" and proposal["exact_target"] == ["note.txt"]
    assert "-beta" in proposal["unified_diff"] and "+gamma" in proposal["unified_diff"]
    assert proposal["rollback_available"] is True
    with pytest.raises(CodexAppServerError, match="Exact"):
        harness.decide_approval(proposal["approval_id"], phrase="wrong", owner_session_digest="b" * 64, approve=True)
    result = harness.decide_approval(
        proposal["approval_id"], phrase=proposal["approval_phrase"],
        owner_session_digest="b" * 64, approve=True,
    )
    assert result["status"] == "APPLIED" and result["rollback_available"] is True
    assert result["workspace_plan_id"].startswith("wplan_")
    assert harness._rpc.responses[-1][1] == {"decision": "accept"}
    with pytest.raises(CodexAppServerError, match="already used"):
        harness.decide_approval(proposal["approval_id"], phrase=proposal["approval_phrase"], owner_session_digest="b" * 64, approve=True)
