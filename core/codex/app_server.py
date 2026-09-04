"""Supervised Codex App Server bridge with governed MNE dynamic tools.

The child process receives a sanitized workspace mirror and a stripped
environment.  It cannot see the repository credential files or use network
commands to bypass P7/P10.  All real repository and infrastructure mutations
remain in the existing server-owned approval engines.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import queue
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
from collections import deque
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from core.llm.external_authorization import ExternalDataPolicy
from core.tools.broker import ToolBroker


CODEX_PROVIDER_ID = "prv_codex_app_server"
CODEX_SERVICE_TIER = "fast"
CODEX_SANDBOX = "workspace-write"
CODEX_APPROVAL_POLICY = "untrusted"


class CodexAppServerError(RuntimeError):
    pass


def discover_repository_root(start: Path) -> Path:
    """Resolve the active checkout or worktree without a hard-coded path."""
    candidate = start.resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=candidate,
            shell=False,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip()).resolve()
    except (OSError, subprocess.SubprocessError):
        pass
    for item in (candidate, *candidate.parents):
        if (item / ".git").exists():
            return item.resolve()
    raise CodexAppServerError("Active repository root could not be discovered.")


class SanitizedWorkspace:
    """Per-thread repository mirror that excludes credentials and VCS state."""

    _EXCLUDED_DIRS = {
        ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
        ".mypy_cache", ".ruff_cache", ".tox", "dist", "build",
    }
    _EXCLUDED_FILES = {
        "config/api_keys_storage.json",
        "config/chatgpt_oauth_tokens.json",
        "operations/actions/audit_log.jsonl",
    }
    _SECRET_SUFFIXES = {".pem", ".pfx", ".p12", ".key", ".kdbx"}

    def __init__(self, real_root: Path, gui_thread_id: str):
        self.real_root = real_root.resolve()
        safe_id = re.sub(r"[^A-Za-z0-9_-]", "-", gui_thread_id)[:80]
        self.root = Path(tempfile.mkdtemp(prefix=f"mne-codex-{safe_id}-")).resolve()
        self._copy()

    @classmethod
    def is_excluded(cls, relative: str, *, is_dir: bool = False) -> bool:
        normalized = relative.replace("\\", "/")
        while normalized.startswith("./"):
            normalized = normalized[2:]
        normalized = normalized.lstrip("/")
        parts = normalized.split("/") if normalized else []
        if any(part in cls._EXCLUDED_DIRS for part in parts):
            return True
        name = parts[-1].casefold() if parts else ""
        if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
            return True
        if normalized.casefold() in {item.casefold() for item in cls._EXCLUDED_FILES}:
            return True
        if not is_dir and Path(name).suffix.casefold() in cls._SECRET_SUFFIXES:
            return True
        return False

    def _copy(self) -> None:
        for source_dir, dirnames, filenames in os.walk(self.real_root, followlinks=False):
            source = Path(source_dir)
            relative_dir = source.relative_to(self.real_root)
            dirnames[:] = [
                name for name in dirnames
                if not self.is_excluded(str(relative_dir / name), is_dir=True)
                and not (source / name).is_symlink()
            ]
            destination = self.root / relative_dir
            destination.mkdir(parents=True, exist_ok=True)
            for filename in filenames:
                relative = relative_dir / filename
                source_file = source / filename
                if self.is_excluded(str(relative)) or source_file.is_symlink():
                    continue
                try:
                    if source_file.stat().st_size > 10_000_000:
                        continue
                    shutil.copy2(source_file, destination / filename)
                except OSError:
                    continue

    def cleanup(self) -> None:
        """Remove only the validated temporary mirror created for this thread."""
        target = self.root.resolve()
        temporary_root = Path(tempfile.gettempdir()).resolve()
        if target.parent != temporary_root or not target.name.startswith("mne-codex-"):
            raise CodexAppServerError("Refusing to remove an unrecognized Codex workspace path.")
        if target.exists():
            shutil.rmtree(target)

    def relative_real_path(self, shadow_path: str) -> str:
        candidate = Path(shadow_path).resolve()
        try:
            relative = candidate.relative_to(self.root)
        except ValueError as exc:
            raise CodexAppServerError("Codex proposed a file outside its sanitized workspace.") from exc
        normalized = str(relative).replace("\\", "/")
        if self.is_excluded(normalized):
            raise CodexAppServerError("Codex proposed a protected workspace path.")
        return normalized


class _JsonRpcProcess:
    def __init__(
        self,
        binary: str,
        *,
        environment: dict[str, str],
        notification_handler: Callable[[str, dict[str, Any]], None],
        request_handler: Callable[[Any, str, dict[str, Any]], None],
        exit_handler: Callable[[str], None],
    ):
        self.binary = binary
        self.environment = environment
        self.notification_handler = notification_handler
        self.request_handler = request_handler
        self.exit_handler = exit_handler
        self.process: subprocess.Popen[str] | None = None
        self._request_id = 0
        self._pending: dict[int, queue.Queue[dict[str, Any]]] = {}
        self._write_lock = threading.RLock()
        self._pending_lock = threading.RLock()
        self._stderr = deque(maxlen=40)
        self.initialized = False

    def start(self) -> None:
        if self.process is not None and self.process.poll() is None:
            return
        argv = [
            self.binary,
            "-c", f'service_tier="{CODEX_SERVICE_TIER}"',
            "app-server", "--listen", "stdio://",
        ]
        try:
            self.process = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=self.environment,
            )
        except OSError as exc:
            raise CodexAppServerError("Codex App Server could not be launched.") from exc
        threading.Thread(target=self._read_stdout, name="codex-app-server-stdout", daemon=True).start()
        threading.Thread(target=self._read_stderr, name="codex-app-server-stderr", daemon=True).start()
        response = self.request(
            "initialize",
            {
                "clientInfo": {"name": "mne_brain", "title": "MNE Brain", "version": "2.0"},
                "capabilities": {"experimentalApi": True},
            },
            timeout=20,
        )
        if not isinstance(response, dict):
            raise CodexAppServerError("Codex App Server initialization returned an invalid response.")
        self.notify("initialized")
        self.initialized = True

    def stop(self) -> None:
        process = self.process
        self.initialized = False
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def request(self, method: str, params: dict[str, Any], *, timeout: float = 30) -> dict[str, Any]:
        process = self.process
        if process is None or process.poll() is not None:
            raise CodexAppServerError("Codex App Server is not running.")
        with self._pending_lock:
            self._request_id += 1
            request_id = self._request_id
            waiter: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)
            self._pending[request_id] = waiter
        self._send({"id": request_id, "method": method, "params": params})
        try:
            message = waiter.get(timeout=max(1.0, timeout))
        except queue.Empty as exc:
            with self._pending_lock:
                self._pending.pop(request_id, None)
            raise CodexAppServerError(f"Codex App Server timed out during {method}.") from exc
        if "error" in message:
            error = message.get("error") if isinstance(message.get("error"), dict) else {}
            detail = ExternalDataPolicy.redact_text(str(error.get("message", "request rejected")))[:500]
            raise CodexAppServerError(f"Codex App Server rejected {method}: {detail}")
        return deepcopy(message.get("result", {}))

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {"method": method}
        if params is not None:
            payload["params"] = params
        self._send(payload)

    def respond(self, request_id: Any, *, result: dict[str, Any] | None = None, error: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {"id": request_id}
        if error is not None:
            payload["error"] = error
        else:
            payload["result"] = result or {}
        self._send(payload)

    def _send(self, payload: dict[str, Any]) -> None:
        process = self.process
        if process is None or process.poll() is not None or process.stdin is None:
            raise CodexAppServerError("Codex App Server connection is closed.")
        serialized = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        with self._write_lock:
            process.stdin.write(serialized + "\n")
            process.stdin.flush()

    def _read_stdout(self) -> None:
        process = self.process
        if process is None or process.stdout is None:
            return
        try:
            for raw_line in process.stdout:
                try:
                    message = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if "id" in message and "method" not in message:
                    with self._pending_lock:
                        waiter = self._pending.pop(message["id"], None)
                    if waiter is not None:
                        waiter.put(message)
                    continue
                method = str(message.get("method", ""))
                params = message.get("params", {})
                if "id" in message and method:
                    threading.Thread(
                        target=self.request_handler,
                        args=(message["id"], method, params if isinstance(params, dict) else {}),
                        name="codex-app-server-request",
                        daemon=True,
                    ).start()
                elif method:
                    self.notification_handler(method, params if isinstance(params, dict) else {})
        finally:
            self.initialized = False
            with self._pending_lock:
                pending = list(self._pending.values())
                self._pending.clear()
            for waiter in pending:
                try:
                    waiter.put_nowait({"error": {"message": "Codex App Server exited."}})
                except queue.Full:
                    pass
            self.exit_handler("CODEX_APP_SERVER_EXITED")

    def _read_stderr(self) -> None:
        process = self.process
        if process is None or process.stderr is None:
            return
        for line in process.stderr:
            safe = ExternalDataPolicy.redact_text(line.strip())
            if safe:
                self._stderr.append(safe[:1000])

    @property
    def stderr_tail(self) -> list[str]:
        return list(self._stderr)[-10:]


class CodexAppServerHarness:
    """Codex thread/turn bridge used by the existing ConversationEngine."""

    _DYNAMIC_TOOLS = {
        "mne_build_evidence": "mne.build_evidence",
        "mne_plan_investigation": "mne.plan_investigation",
        "mne_prepare_live_read": "mne.prepare_live_read",
        "owner_direct_discover": "owner_direct.discover",
        "owner_direct_prepare_write": "owner_direct.prepare_write",
        "owner_direct_identity_audit": "owner_direct.identity_audit",
        "p10_prepare": "p10.prepare",
        "p10_prepare_critical": "p10.prepare_critical",
    }
    _SECRET_ENV_MARKERS = (
        "API_KEY", "PASSWORD", "PASSWD", "TOKEN", "SECRET", "CREDENTIAL",
        "PRIVATE_KEY", "ACCESS_KEY", "AUTHORIZATION",
    )
    _BLOCKED_COMMANDS = re.compile(
        r"(?i)(?:^|[\s;&|])(ssh|scp|sftp|plink|pscp|winrs|enter-pssession|invoke-command|"
        r"curl|wget|invoke-webrequest|invoke-restmethod|snmpwalk|mysql|sqlcmd|psql)\b"
    )
    _SAFE_READ_COMMAND = re.compile(
        r"(?i)^(?:get-content|get-childitem|select-string|test-path|resolve-path|get-item|get-location|"
        r"measure-object|rg(?:\.exe)?|where(?:\.exe)?|git\s+(?:status|diff|log|show|branch|rev-parse|ls-files|grep)\b|"
        r"python(?:\.exe)?\s+-m\s+(?:pytest|compileall)\b|node(?:\.exe)?\s+--check\b)"
    )
    _SAFE_PIPE_COMMAND = re.compile(r"(?i)^(?:where-object|select-object|sort-object|measure-object)\b")
    _QUOTED_WINDOWS_PATH = re.compile(r"['\"]([A-Za-z]:[\\/][^'\"\r\n]+)['\"]")
    _UNQUOTED_WINDOWS_PATH = re.compile(r"(?<![\w'\"])([A-Za-z]:[\\/][^\s|;<>`'\"]+)")
    _PROTECTED_READ_NAME = re.compile(r"(?i)(?:^\.env(?:\.|$)|password|passwd|credential|access[_-]?token|refresh[_-]?token|api[_-]?key|auth\.json$)")

    def __init__(
        self,
        base_dir: Path,
        *,
        tool_broker: ToolBroker,
        event_sink: Callable[[str, str, str, dict[str, Any]], None],
        completion_sink: Callable[[str, str, str | None], None],
        failure_sink: Callable[[str, str], None],
    ):
        self.base_dir = discover_repository_root(base_dir)
        self.tool_broker = tool_broker
        self.event_sink = event_sink
        self.completion_sink = completion_sink
        self.failure_sink = failure_sink
        self.binary = self._find_binary()
        self._rpc: _JsonRpcProcess | None = None
        self._lock = threading.RLock()
        self._threads: dict[str, dict[str, Any]] = {}
        self._codex_threads: dict[str, str] = {}
        self._turns_by_codex: dict[str, dict[str, Any]] = {}
        self._turns_by_gui: dict[str, dict[str, Any]] = {}
        self._items: dict[str, dict[str, Any]] = {}
        self._approvals: dict[str, dict[str, Any]] = {}
        self._request_to_approval: dict[Any, str] = {}
        self._restart_count = 0
        self._last_failure: str | None = None

    @staticmethod
    def _find_binary() -> str | None:
        for name in ("codex.exe", "codex.cmd", "codex"):
            candidate = shutil.which(name)
            if candidate:
                return candidate
        return None

    @classmethod
    def _child_environment(cls) -> dict[str, str]:
        # Deliberately reconstruct a minimal environment. The API process has
        # loaded .env credentials, so copying its environment and filtering by
        # guessed secret names is not a sufficient isolation boundary.
        allowed = {
            "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP",
            "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA",
            "PROGRAMDATA", "USERNAME", "USERDOMAIN", "PROCESSOR_ARCHITECTURE",
            "NUMBER_OF_PROCESSORS", "CODEX_HOME", "LANG", "LC_ALL", "TERM",
        }
        environment = {key: value for key, value in os.environ.items() if key.upper() in allowed}
        environment["MNE_BRAIN_CODEX_CHILD"] = "1"
        return environment

    def start(self) -> None:
        with self._lock:
            if self.binary is None:
                raise CodexAppServerError("Codex binary was not found on PATH.")
            if self._rpc is not None and self._rpc.process is not None and self._rpc.process.poll() is None and self._rpc.initialized:
                return
            rpc: _JsonRpcProcess | None = None
            rpc = _JsonRpcProcess(
                self.binary,
                environment=self._child_environment(),
                notification_handler=self._on_notification,
                request_handler=self._on_server_request,
                exit_handler=lambda reason: self._on_exit(reason, rpc),
            )
            self._rpc = rpc
            rpc.start()
            self._last_failure = None
            mappings = list(self._threads.items())
        for gui_thread_id, mapping in mappings:
            codex_thread_id = mapping.get("codex_thread_id")
            if not codex_thread_id:
                continue
            try:
                result = self._rpc.request(
                    "thread/resume",
                    {
                        "threadId": codex_thread_id,
                        "cwd": str(mapping["workspace"].root),
                        "sandbox": CODEX_SANDBOX,
                        "approvalPolicy": CODEX_APPROVAL_POLICY,
                        "serviceTier": CODEX_SERVICE_TIER,
                        "developerInstructions": self._developer_instructions(),
                    },
                    timeout=30,
                )
                resumed = result.get("thread", {}).get("id")
                if resumed:
                    with self._lock:
                        mapping["codex_thread_id"] = resumed
                        self._codex_threads[resumed] = gui_thread_id
            except CodexAppServerError:
                with self._lock:
                    mapping["codex_thread_id"] = None

    def stop(self, *, cleanup_workspaces: bool = False) -> None:
        with self._lock:
            rpc = self._rpc
            self._rpc = None
            workspaces = [mapping.get("workspace") for mapping in self._threads.values()]
        if rpc is not None:
            rpc.stop()
        if cleanup_workspaces:
            for workspace in workspaces:
                if isinstance(workspace, SanitizedWorkspace):
                    workspace.cleanup()

    def readiness(self, *, start_process: bool = False) -> dict[str, Any]:
        missing: list[str] = []
        binary_found = self.binary is not None
        version_ok = False
        authenticated = False
        app_help = False
        if not binary_found:
            missing.append("Codex CLI is not installed or not on PATH.")
        else:
            environment = self._child_environment()
            try:
                version = subprocess.run(
                    [self.binary, "--version"], shell=False, capture_output=True, text=True,
                    timeout=15, check=False, env=environment,
                )
                version_ok = version.returncode == 0
            except (OSError, subprocess.SubprocessError):
                version_ok = False
            try:
                login = subprocess.run(
                    [self.binary, "-c", f'service_tier="{CODEX_SERVICE_TIER}"', "login", "status"],
                    shell=False, capture_output=True, text=True, timeout=15, check=False, env=environment,
                )
                authenticated = login.returncode == 0 and "Logged in using ChatGPT" in (login.stdout + login.stderr)
            except (OSError, subprocess.SubprocessError):
                authenticated = False
            try:
                help_result = subprocess.run(
                    [self.binary, "-c", f'service_tier="{CODEX_SERVICE_TIER}"', "app-server", "--help"],
                    shell=False, capture_output=True, text=True, timeout=15, check=False, env=environment,
                )
                app_help = help_result.returncode == 0
            except (OSError, subprocess.SubprocessError):
                app_help = False
            if not authenticated:
                missing.append("ChatGPT authentication is unavailable; run `codex login` as this Windows user.")
            if not app_help:
                missing.append("`codex app-server --help` did not complete successfully.")
            if not version_ok:
                missing.append("`codex --version` did not complete successfully.")
        if start_process and binary_found and version_ok and authenticated and app_help:
            try:
                self.start()
            except CodexAppServerError:
                missing.append("Codex App Server could not initialize.")
        rpc = self._rpc
        initialized = bool(rpc and rpc.initialized and rpc.process and rpc.process.poll() is None)
        return {
            "status": "READY" if binary_found and version_ok and authenticated and app_help and initialized else "BLOCKED",
            "codex_binary_found": binary_found,
            "version_check_passed": version_ok,
            "chatgpt_authenticated": authenticated,
            "app_server_help_available": app_help,
            "app_server_initialized": initialized,
            "repository_root": str(self.base_dir),
            "sandbox": CODEX_SANDBOX,
            "network_access": False,
            "approval_policy": CODEX_APPROVAL_POLICY,
            "service_tier": CODEX_SERVICE_TIER,
            "service_tier_overridden": True,
            "openai_api_key_inherited": False,
            "restart_count": self._restart_count,
            "missing_prerequisites": missing,
            "last_failure": self._last_failure,
            "secrets_returned": False,
        }

    def ensure_thread(self, gui_thread_id: str, permission_mode: str = "OWNER_DIRECT") -> dict[str, Any]:
        self.start()
        with self._lock:
            existing = self._threads.get(gui_thread_id)
            if existing and existing.get("codex_thread_id"):
                return existing
            workspace = existing.get("workspace") if existing else SanitizedWorkspace(self.base_dir, gui_thread_id)
        tools = []
        allowed = self.tool_broker.permissions.modes[permission_mode]
        aliases = {internal: alias for alias, internal in self._DYNAMIC_TOOLS.items()}
        for tool in self.tool_broker.registry.provider_tools(allowed):
            if tool["name"] not in aliases:
                continue
            tools.append({
                "name": aliases[tool["name"]],
                "description": tool["description"],
                "inputSchema": tool["input_schema"],
                "deferLoading": False,
            })
        rpc = self._require_rpc()
        result = rpc.request(
            "thread/start",
            {
                "cwd": str(workspace.root),
                "sandbox": CODEX_SANDBOX,
                "approvalPolicy": CODEX_APPROVAL_POLICY,
                "approvalsReviewer": "user",
                "serviceTier": CODEX_SERVICE_TIER,
                "ephemeral": False,
                "dynamicTools": tools,
                "developerInstructions": self._developer_instructions(),
            },
            timeout=45,
        )
        codex_thread_id = str(result.get("thread", {}).get("id", ""))
        if not codex_thread_id:
            raise CodexAppServerError("Codex App Server did not create a thread.")
        mapping = {"codex_thread_id": codex_thread_id, "workspace": workspace, "permission_mode": permission_mode}
        with self._lock:
            self._threads[gui_thread_id] = mapping
            self._codex_threads[codex_thread_id] = gui_thread_id
        return mapping

    def start_turn(self, *, gui_thread_id: str, gui_turn_id: str, content: str, owner_session_digest: str, permission_mode: str = "OWNER_DIRECT") -> None:
        mapping = self.ensure_thread(gui_thread_id, permission_mode)
        rpc = self._require_rpc()
        result = rpc.request(
            "turn/start",
            {
                "threadId": mapping["codex_thread_id"],
                "input": [{"type": "text", "text": content}],
                "approvalPolicy": CODEX_APPROVAL_POLICY,
                "sandboxPolicy": {
                    "type": "workspaceWrite",
                    "writableRoots": [str(mapping["workspace"].root)],
                    "networkAccess": False,
                    "excludeSlashTmp": True,
                    "excludeTmpdirEnvVar": True,
                },
                "serviceTier": CODEX_SERVICE_TIER,
            },
            timeout=45,
        )
        codex_turn_id = str(result.get("turn", {}).get("id", ""))
        if not codex_turn_id:
            raise CodexAppServerError("Codex App Server did not start a turn.")
        state = {
            "gui_thread_id": gui_thread_id,
            "gui_turn_id": gui_turn_id,
            "codex_thread_id": mapping["codex_thread_id"],
            "codex_turn_id": codex_turn_id,
            "owner_session_digest": owner_session_digest,
            "permission_mode": mapping.get("permission_mode", permission_mode),
            "final_text": [],
            "authoritative_final_text": "",
            "progress_text": [],
            "active": True,
        }
        with self._lock:
            self._turns_by_codex[codex_turn_id] = state
            self._turns_by_gui[gui_turn_id] = state

    def cancel(self, gui_turn_id: str) -> None:
        with self._lock:
            state = deepcopy(self._turns_by_gui.get(gui_turn_id))
        if not state:
            return
        self._require_rpc().request(
            "turn/interrupt",
            {"threadId": state["codex_thread_id"], "turnId": state["codex_turn_id"]},
            timeout=15,
        )

    def decide_approval(self, approval_id: str, *, phrase: str | None, owner_session_digest: str, approve: bool) -> dict[str, Any]:
        with self._lock:
            item = self._approvals.get(approval_id)
            if item is None or item["used"]:
                raise CodexAppServerError("Codex approval is unavailable or already used.")
            if datetime.now(timezone.utc) > datetime.fromisoformat(item["expires_at"]):
                raise CodexAppServerError("Codex approval expired.")
            if item["owner_session_digest"] != owner_session_digest:
                raise CodexAppServerError("Codex approval belongs to a different owner session.")
            if approve and phrase != item["approval_phrase"]:
                raise CodexAppServerError("Exact Codex approval phrase required.")
            item["used"] = True
        rpc = self._require_rpc()
        if not approve:
            rpc.respond(item["request_id"], result={"decision": "decline"})
            item["status"] = "DENIED"
            return self._public_approval(item)
        if item["kind"] == "COMMAND":
            if item.get("blocked"):
                rpc.respond(item["request_id"], result={"decision": "decline"})
                item["status"] = "POLICY_BLOCKED"
                return self._public_approval(item)
            rpc.respond(item["request_id"], result={"decision": "accept"})
            item["status"] = "APPROVED_ONCE"
            return self._public_approval(item)
        try:
            plan = self.tool_broker.prepare_patch(item["unified_diff"])
            approval = self.tool_broker.approve_patch(
                plan["plan_id"], plan["approval_phrase"], owner_session_digest=owner_session_digest,
            )
            result = self.tool_broker.apply_approved_patch(
                plan["plan_id"], approval["approval_id"], owner_session_digest=owner_session_digest,
            )
        except Exception as exc:
            rpc.respond(item["request_id"], result={"decision": "decline"})
            item.update({
                "status": "APPLY_FAILED",
                "failure": ExternalDataPolicy.redact_text(str(exc))[:500],
                "rollback_available": False,
            })
            return self._public_approval(item)
        rpc.respond(item["request_id"], result={"decision": "accept"})
        validation = self._post_change_validation()
        item.update({
            "status": result.get("status", "UNCERTAIN"),
            "workspace_plan_id": plan["plan_id"],
            "rollback_available": bool(result.get("rollback_available")),
            "validation": validation,
        })
        return self._public_approval(item)

    def _post_change_validation(self) -> dict[str, Any]:
        try:
            result = subprocess.run(
                ["git", "diff", "--check"], cwd=self.base_dir, shell=False,
                capture_output=True, text=True, timeout=30, check=False,
            )
            return {
                "check": "git diff --check",
                "status": "PASSED" if result.returncode == 0 else "FAILED",
                "returncode": result.returncode,
                "output": ExternalDataPolicy.redact_text((result.stdout + result.stderr)[-4000:]),
            }
        except (OSError, subprocess.SubprocessError):
            return {"check": "git diff --check", "status": "FAILED", "returncode": None, "output": "Validation could not run."}

    def _on_server_request(self, request_id: Any, method: str, params: dict[str, Any]) -> None:
        try:
            if method == "item/tool/call":
                self._execute_dynamic_tool(request_id, params)
                return
            if method in {"item/commandExecution/requestApproval", "item/fileChange/requestApproval"}:
                self._prepare_approval(request_id, method, params)
                return
            self._require_rpc().respond(
                request_id,
                error={"code": -32601, "message": "This server request is not supported by the governed GUI."},
            )
        except Exception as exc:
            try:
                self._require_rpc().respond(
                    request_id,
                    error={"code": -32000, "message": ExternalDataPolicy.redact_text(str(exc))[:500]},
                )
            except Exception:
                pass

    def _execute_dynamic_tool(self, request_id: Any, params: dict[str, Any]) -> None:
        codex_turn_id = str(params.get("turnId", ""))
        with self._lock:
            state = self._turns_by_codex.get(codex_turn_id)
        if state is None:
            raise CodexAppServerError("Dynamic tool call was not bound to an active GUI turn.")
        requested_tool = str(params.get("tool", ""))
        tool_name = self._DYNAMIC_TOOLS.get(requested_tool)
        if tool_name is None:
            raise CodexAppServerError("Codex requested a tool outside the governed MNE set.")
        arguments = params.get("arguments", {})
        call = self.tool_broker.propose(
            thread_id=state["gui_thread_id"], turn_id=state["gui_turn_id"],
            tool_name=tool_name, arguments=arguments if isinstance(arguments, dict) else {},
            permission_mode=state.get("permission_mode", "OWNER_DIRECT"),
        )
        self.event_sink(state["gui_thread_id"], state["gui_turn_id"], "tool.proposed", {
            "tool_call_id": call["tool_call_id"], "tool_name": tool_name,
            "argument_digest": call["argument_digest"], "status": "AUTOMATIC_READ" if (tool_name.startswith("mne.") or tool_name == "owner_direct.discover" or tool_name == "owner_direct.identity_audit") else "AUTOMATIC_PREPARATION",
        })
        try:
            if tool_name == "mne.prepare_live_read":
                result = self.tool_broker.run_owner_autonomous_live_read(
                    arguments, owner_session_digest=state["owner_session_digest"], tool_call_id=call["tool_call_id"],
                )
                envelope = {"tool_call_id": call["tool_call_id"], "status": result.get("status", "COMPLETED"), "result": result}
            else:
                envelope = self.tool_broker.invoke(call["tool_call_id"], owner_session_digest=state["owner_session_digest"])
            self.event_sink(state["gui_thread_id"], state["gui_turn_id"], "tool.completed", {
                "tool_call_id": call["tool_call_id"], "tool_name": tool_name, "result": envelope.get("result"),
            })
            safe = self._sanitize_payload(envelope)
            self._require_rpc().respond(request_id, result={
                "success": True,
                "contentItems": [{"type": "inputText", "text": json.dumps(safe, ensure_ascii=False, sort_keys=True)[:200000]}],
            })
        except Exception as exc:
            message = ExternalDataPolicy.redact_text(str(exc))[:1000]
            self.event_sink(state["gui_thread_id"], state["gui_turn_id"], "tool.completed", {
                "tool_call_id": call["tool_call_id"], "tool_name": tool_name,
                "result": {"status": "FAILED", "message": message},
            })
            self._require_rpc().respond(request_id, result={
                "success": False,
                "contentItems": [{"type": "inputText", "text": message}],
            })

    def _prepare_approval(self, request_id: Any, method: str, params: dict[str, Any]) -> None:
        codex_turn_id = str(params.get("turnId", ""))
        with self._lock:
            state = self._turns_by_codex.get(codex_turn_id)
            item_details = deepcopy(self._items.get(str(params.get("itemId", "")), {}))
        if state is None:
            raise CodexAppServerError("Approval request was not bound to an active GUI turn.")
        kind = "FILE_CHANGE" if method == "item/fileChange/requestApproval" else "COMMAND"
        approval_id = "cappr_" + secrets.token_urlsafe(18)
        created = datetime.now(timezone.utc)
        payload: dict[str, Any] = {
            "approval_id": approval_id,
            "request_id": request_id,
            "kind": kind,
            "gui_thread_id": state["gui_thread_id"],
            "gui_turn_id": state["gui_turn_id"],
            "codex_turn_id": codex_turn_id,
            "item_id": str(params.get("itemId", "")),
            "owner_session_digest": state["owner_session_digest"],
            "created_at": created.isoformat(),
            "expires_at": (created + timedelta(minutes=5)).isoformat(),
            "used": False,
            "status": "APPROVAL_REQUIRED",
            "prechecks": ["Owner session binding", "single-use digest", "workspace boundary", "protected-path exclusion"],
            "post_change_validation": ["git diff --check", "Codex task validation", "separate rollback preparation"],
        }
        if kind == "FILE_CHANGE":
            changes = item_details.get("changes", [])
            mapping = self._threads[state["gui_thread_id"]]
            unified_diff, paths = self._build_unified_diff(mapping["workspace"], changes)
            digest = hashlib.sha256(unified_diff.encode("utf-8")).hexdigest()
            payload.update({
                "exact_target": paths,
                "unified_diff": unified_diff,
                "change_digest": digest,
                "expected_impact": "Modify only the displayed repository paths.",
                "risk_level": 2,
                "risk_explanation": "Repository content will change; tests may fail until validation completes.",
                "rollback_available": True,
                "rollback_procedure": "Prepare the server-generated reverse diff after application; rollback requires a separate exact owner approval.",
                "approval_phrase": f"APPROVE CODEX FILES {approval_id} {digest}",
            })
        else:
            command = str(params.get("command") or item_details.get("command") or "")
            blocked = bool(self._BLOCKED_COMMANDS.search(command))
            digest = hashlib.sha256(command.encode("utf-8")).hexdigest()
            payload.update({
                "exact_target": str(params.get("cwd") or item_details.get("cwd") or self._threads[state["gui_thread_id"]]["workspace"].root),
                "command": command,
                "command_digest": digest,
                "expected_impact": "Run the displayed command only inside the disposable sanitized workspace.",
                "risk_level": 4 if blocked else 2,
                "risk_explanation": "Direct infrastructure or network commands are blocked; other untrusted commands require one-time approval.",
                "rollback_available": False,
                "rollback_procedure": "The command runs only in a disposable mirror. Real repository writes require a separate file-change event.",
                "blocked": blocked,
                "approval_phrase": f"APPROVE CODEX COMMAND {approval_id} {digest}",
            })
            if blocked:
                payload.update({"status": "POLICY_BLOCKED", "used": True})
                self._require_rpc().respond(request_id, result={"decision": "decline"})
                self.event_sink(state["gui_thread_id"], state["gui_turn_id"], "tool.completed", self._public_approval(payload))
                return
            if self._is_safe_shadow_command(item_details, self._threads[state["gui_thread_id"]]["workspace"]):
                payload.update({"status": "AUTOMATIC_READ", "used": True})
                self._require_rpc().respond(request_id, result={"decision": "accept"})
                self.event_sink(state["gui_thread_id"], state["gui_turn_id"], "tool.proposed", {
                    "tool_call_id": approval_id,
                    "tool_name": "workspace.safe_command",
                    "argument_digest": digest,
                    "status": "AUTOMATIC_READ",
                })
                return
        with self._lock:
            self._approvals[approval_id] = payload
            self._request_to_approval[request_id] = approval_id
        self.event_sink(state["gui_thread_id"], state["gui_turn_id"], "tool.approval_required", self._public_approval(payload))

    @classmethod
    def _is_safe_shadow_command(cls, item: dict[str, Any], workspace: SanitizedWorkspace) -> bool:
        try:
            cwd = Path(str(item.get("cwd", ""))).resolve()
            cwd.relative_to(workspace.root)
        except (OSError, ValueError):
            return False
        actions = item.get("commandActions", [])
        commands = [str(action.get("command", "")) for action in actions if isinstance(action, dict)]
        if not commands:
            return False
        for command in commands:
            stripped = command.strip()
            lowered = stripped.casefold()
            pipeline = [part.strip() for part in stripped.split("|")]
            if not stripped or not pipeline or not cls._SAFE_READ_COMMAND.match(pipeline[0]):
                return False
            if any(not cls._SAFE_PIPE_COMMAND.match(part) for part in pipeline[1:]):
                return False
            if re.search(r"[;&<>`]", stripped) or "$(" in stripped or "::" in stripped:
                return False
            if ".." in stripped or ".env" in lowered:
                return False
            absolute_paths = cls._absolute_windows_paths(stripped)
            if re.search(r"(?i)\b[A-Z]:[\\/]", stripped) and not absolute_paths:
                return False
            if any(not cls._is_trusted_read_path(path, workspace) for path in absolute_paths):
                return False
            remaining_variables = re.sub(r"(?i)\$_|\$null\b", "", stripped)
            if "$" in remaining_variables or "%" in stripped or "~" in stripped:
                return False
            if re.search(r"(?i)\b(?:set-content|add-content|out-file|remove-item|move-item|copy-item|new-item|tee-object)\b", stripped):
                return False
        return True

    @classmethod
    def _absolute_windows_paths(cls, command: str) -> list[Path]:
        values = cls._QUOTED_WINDOWS_PATH.findall(command)
        values.extend(cls._UNQUOTED_WINDOWS_PATH.findall(command))
        unique: list[Path] = []
        seen: set[str] = set()
        for value in values:
            normalized = value.rstrip(",)")
            key = normalized.casefold()
            if key in seen:
                continue
            seen.add(key)
            unique.append(Path(normalized).resolve())
        return unique

    @staticmethod
    def _trusted_read_roots() -> tuple[Path, ...]:
        home = Path.home().resolve()
        codex_home = Path(os.getenv("CODEX_HOME", str(home / ".codex"))).resolve()
        candidates = (
            codex_home / "skills",
            codex_home / "memories",
            codex_home / "attachments",
            codex_home / "plugins" / "cache",
            home / ".agents" / "skills",
        )
        return tuple(path.resolve() for path in candidates if path.is_dir())

    @classmethod
    def _is_trusted_read_path(cls, path: Path, workspace: SanitizedWorkspace) -> bool:
        candidate = path.resolve()
        if cls._PROTECTED_READ_NAME.search(candidate.name) or candidate.suffix.casefold() in SanitizedWorkspace._SECRET_SUFFIXES:
            return False
        roots = (workspace.root, *cls._trusted_read_roots())
        for root in roots:
            try:
                candidate.relative_to(root.resolve())
                return True
            except ValueError:
                continue
        return False

    def _build_unified_diff(self, workspace: SanitizedWorkspace, changes: list[dict[str, Any]]) -> tuple[str, list[str]]:
        sections: list[str] = []
        paths: list[str] = []
        for change in changes:
            relative = workspace.relative_real_path(str(change.get("path", "")))
            paths.append(relative)
            kind = str((change.get("kind") or {}).get("type", "update"))
            diff = str(change.get("diff", ""))
            old_path = f"a/{relative}"
            new_path = f"b/{relative}"
            if kind == "update" and diff.lstrip().startswith("@@"):
                sections.append(f"diff --git {old_path} {new_path}\n--- {old_path}\n+++ {new_path}\n{diff.rstrip()}\n")
                continue
            real_file = workspace.real_root / relative
            old_text = real_file.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True) if real_file.is_file() else []
            if kind == "delete":
                new_text: list[str] = []
            else:
                new_text = diff.splitlines(keepends=True)
                if diff and not diff.endswith(("\n", "\r")):
                    new_text[-1] += "\n"
            header_old = "/dev/null" if kind == "add" else old_path
            header_new = "/dev/null" if kind == "delete" else new_path
            body = "".join(difflib.unified_diff(old_text, new_text, fromfile=header_old, tofile=header_new, lineterm="\n"))
            mode_header = "new file mode 100644\n" if kind == "add" else "deleted file mode 100644\n" if kind == "delete" else ""
            sections.append(f"diff --git {old_path} {new_path}\n{mode_header}{body}")
        if not sections or not paths:
            raise CodexAppServerError("Codex file change did not contain a reviewable diff.")
        return "".join(sections), paths

    def _on_notification(self, method: str, params: dict[str, Any]) -> None:
        codex_turn_id = str(params.get("turnId") or (params.get("turn") or {}).get("id") or "")
        with self._lock:
            state = self._turns_by_codex.get(codex_turn_id)
        if state is None:
            return
        gui_thread_id = state["gui_thread_id"]
        gui_turn_id = state["gui_turn_id"]
        if method == "item/started":
            item = params.get("item", {})
            if isinstance(item, dict) and item.get("id"):
                with self._lock:
                    self._items[str(item["id"])] = deepcopy(item)
            item_type = str(item.get("type", "")) if isinstance(item, dict) else ""
            if item_type == "commandExecution":
                self.event_sink(gui_thread_id, gui_turn_id, "command.started", self._sanitize_payload(item))
            elif item_type == "fileChange":
                self.event_sink(gui_thread_id, gui_turn_id, "file.change", self._safe_file_item(state, item))
            elif item_type == "dynamicToolCall":
                self.event_sink(gui_thread_id, gui_turn_id, "tool.started", self._sanitize_payload(item))
            return
        if method == "item/agentMessage/delta":
            text = str(params.get("delta", ""))
            item_id = str(params.get("itemId", ""))
            with self._lock:
                phase = str(self._items.get(item_id, {}).get("phase", ""))
                if phase == "final_answer":
                    state["final_text"].append(text)
                else:
                    state["progress_text"].append(text)
            self.event_sink(gui_thread_id, gui_turn_id, "answer.delta" if phase == "final_answer" else "agent.progress", {"text": text, "phase": phase or "commentary"})
            return
        if method == "turn/plan/updated":
            self.event_sink(gui_thread_id, gui_turn_id, "agent.plan", self._sanitize_payload(params))
            return
        if method in {"item/commandExecution/outputDelta", "item/commandExecution/terminalInteraction"}:
            self.event_sink(gui_thread_id, gui_turn_id, "command.output", {"delta": ExternalDataPolicy.redact_text(str(params.get("delta", "")))[:20000], "item_id": params.get("itemId")})
            return
        if method == "turn/diff/updated":
            self.event_sink(gui_thread_id, gui_turn_id, "file.diff", {"diff": ExternalDataPolicy.redact_text(str(params.get("diff", "")))[:200000]})
            return
        if method == "item/completed":
            item = params.get("item", {})
            item_type = str(item.get("type", "")) if isinstance(item, dict) else ""
            if isinstance(item, dict) and item.get("id"):
                with self._lock:
                    previous = self._items.get(str(item["id"]), {})
                    self._items[str(item["id"])] = deepcopy(item)
                    phase = str(item.get("phase") or previous.get("phase") or "")
                    if item_type == "agentMessage" and phase == "final_answer":
                        state["authoritative_final_text"] = str(item.get("text", "")).strip()
            if item_type == "commandExecution":
                self.event_sink(gui_thread_id, gui_turn_id, "command.completed", self._sanitize_payload(item))
            elif item_type == "fileChange":
                self.event_sink(gui_thread_id, gui_turn_id, "file.change", self._safe_file_item(state, item))
            elif item_type == "dynamicToolCall":
                self.event_sink(gui_thread_id, gui_turn_id, "tool.completed", self._sanitize_payload(item))
            return
        if method == "turn/completed":
            turn = params.get("turn", {})
            status = str(turn.get("status", "completed"))
            with self._lock:
                state["active"] = False
                answer = str(state.get("authoritative_final_text", "")).strip()
                if not answer:
                    for item in reversed(turn.get("items", []) if isinstance(turn, dict) else []):
                        if isinstance(item, dict) and item.get("type") == "agentMessage" and item.get("phase") == "final_answer":
                            answer = str(item.get("text", "")).strip()
                            if answer:
                                break
                answer = answer or "".join(state["final_text"]).strip()
            if status == "completed":
                if answer:
                    # Deltas are useful for low latency, but item/completed is the
                    # authoritative App Server state. Reconcile the browser with
                    # the complete text before publishing the terminal event.
                    self.event_sink(gui_thread_id, gui_turn_id, "answer.final", {"text": answer, "phase": "final_answer"})
                    self.completion_sink(gui_thread_id, gui_turn_id, answer)
                else:
                    self.failure_sink(gui_turn_id, "CODEX_EMPTY_RESPONSE")
            elif status == "interrupted":
                self.failure_sink(gui_turn_id, "CODEX_TURN_CANCELLED")
            else:
                self.failure_sink(gui_turn_id, "CODEX_TURN_FAILED")

    def _safe_file_item(self, state: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
        mapping = self._threads[state["gui_thread_id"]]
        safe = {"type": "fileChange", "id": item.get("id"), "status": item.get("status"), "changes": []}
        for change in item.get("changes", []):
            try:
                relative = mapping["workspace"].relative_real_path(str(change.get("path", "")))
            except CodexAppServerError:
                relative = "BLOCKED_OUTSIDE_WORKSPACE"
            safe["changes"].append({"path": relative, "kind": change.get("kind"), "diff": ExternalDataPolicy.redact_text(str(change.get("diff", "")))[:200000]})
        return safe

    def _on_exit(self, reason: str, source: _JsonRpcProcess | None) -> None:
        with self._lock:
            if self._rpc is None or self._rpc is not source:
                return
            self._rpc = None
            self._last_failure = reason
            self._restart_count += 1
            active = [deepcopy(item) for item in self._turns_by_gui.values() if item.get("active")]
        for state in active:
            self.failure_sink(state["gui_turn_id"], "CODEX_APP_SERVER_EXITED")

    def _require_rpc(self) -> _JsonRpcProcess:
        rpc = self._rpc
        if rpc is None or rpc.process is None or rpc.process.poll() is not None or not rpc.initialized:
            self.start()
            rpc = self._rpc
        if rpc is None:
            raise CodexAppServerError("Codex App Server is unavailable.")
        return rpc

    @staticmethod
    def _public_approval(item: dict[str, Any]) -> dict[str, Any]:
        excluded = {"request_id", "owner_session_digest", "used", "blocked"}
        return {key: deepcopy(value) for key, value in item.items() if key not in excluded}

    @classmethod
    def _sanitize_payload(cls, value: Any, *, key: str = "") -> Any:
        """Redact values for local UI/agent transport without dropping reviewable commands."""
        normalized = key.casefold().replace("-", "_")
        if normalized in {
            "password", "passwd", "token", "access_token", "refresh_token", "secret",
            "authorization", "api_key", "private_key", "credential", "credentials",
            "credential_value", "community",
        }:
            return "[REDACTED]"
        if isinstance(value, dict):
            return {str(k): cls._sanitize_payload(v, key=str(k)) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._sanitize_payload(item, key=key) for item in value]
        if isinstance(value, str):
            return ExternalDataPolicy.redact_text(value)
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return ExternalDataPolicy.redact_text(str(value))

    @staticmethod
    def _developer_instructions() -> str:
        return (
            "You are the primary MNE Brain local agent. Investigate before answering: inspect focused workspace evidence, "
            "run safe local diagnostics, use governed MNE dynamic tools for current infrastructure state, validate results, "
            "and continue until the answer is evidence-based. The workspace is a sanitized mirror with no credentials. "
            "Never attempt SSH, REST, WinRM, SNMP, device access, credential discovery, or direct infrastructure commands; "
            "use only the dynamically advertised governed MNE tools. In Owner Direct mode, use owner_direct_discover for one "
            "exact read-only check, owner_direct_identity_audit for requested one-attempt identity audit rows, and "
            "owner_direct_prepare_write only to produce a risk warning; the owner-facing UI alone performs final write confirmation. "
            "In legacy constrained mode, use mne_prepare_live_read for live reads and p10_prepare or p10_prepare_critical for "
            "infrastructure changes. Do not claim a live fact without returned attributable evidence. Safe reads and tests may run automatically. "
            "For automatic reads, issue one simple Get-Content, Get-ChildItem, Select-String, rg, or read-only git command at a time; "
            "repository-mirror, installed-skill, attachment, and memory reads are pre-authorized when the server classifies their exact paths as safe. "
            "do not wrap safe reads in variables, loops, script blocks, or general-purpose Python. "
            "All file changes and untrusted commands must pause for client approval. Explain material risk and validation."
        )
