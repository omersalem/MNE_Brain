"""Supervised OpenCode HTTP/SSE engine with governed MNE tool access only."""

from __future__ import annotations

import base64
import hmac
import http.server
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Iterable

from core.opencode.custom_providers import CustomProviderStore, validate_endpoint
from core.tools.mcp_relay import ALIASES


OPENCODE_PROVIDER_ID = "prv_opencode"
OPENCODE_MINIMUM_VERSION = (1, 0, 0)
OPENCODE_SAFE_ERRORS = {
    "OPENCODE_NOT_INSTALLED",
    "OPENCODE_VERSION_UNSUPPORTED",
    "OPENCODE_AUTH_REQUIRED",
    "OPENCODE_NO_CONNECTED_PROVIDER",
    "OPENCODE_NO_MODELS",
    "OPENCODE_MODEL_REMOVED",
    "OPENCODE_RATE_LIMITED",
    "OPENCODE_SERVER_UNAVAILABLE",
    "OPENCODE_CONNECTION_FAILED",
    "OPENCODE_TIMEOUT",
    "OPENCODE_EMPTY_RESPONSE",
    "OPENCODE_TURN_CANCELLED",
}


class OpenCodeError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code if code in OPENCODE_SAFE_ERRORS else "OPENCODE_CONNECTION_FAILED"
        super().__init__(message)


def _safe_text(value: Any, limit: int = 1000) -> str:
    text = str(value or "").replace("\x00", " ")
    text = re.sub(r"(?i)(bearer|api[_ -]?key|token|password|secret)\s*[:=]\s*\S+", r"\1=[REDACTED]", text)
    return text[:limit]


def _sanitize(value: Any, *, key: str = "") -> Any:
    sensitive = {"authorization", "key", "token", "password", "secret", "refresh", "access", "headers", "raw", "body"}
    if any(item in key.casefold() for item in sensitive):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): _sanitize(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(item, key=key) for item in value[:200]]
    if isinstance(value, str):
        return _safe_text(value, 40_000)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _safe_text(value)


class OpenCodeHTTPClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        raw = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        self._headers = {"Authorization": "Basic " + raw}
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None, *, timeout: float = 15) -> Any:
        data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = dict(self._headers)
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base_url + path, data=data, method=method, headers=headers)
        try:
            with self._opener.open(request, timeout=timeout) as response:
                raw = response.read(8_000_000)
                if response.status == 204 or not raw:
                    return None
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            code = "OPENCODE_AUTH_REQUIRED" if exc.code in {401, 403} else (
                "OPENCODE_RATE_LIMITED" if exc.code == 429 else "OPENCODE_CONNECTION_FAILED"
            )
            raise OpenCodeError(code, "OpenCode rejected the local request.") from exc
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise OpenCodeError("OPENCODE_SERVER_UNAVAILABLE", "OpenCode server is unavailable.") from exc

    def events(self, path: str, *, timeout: float = 30) -> Iterable[dict[str, Any]]:
        request = urllib.request.Request(self.base_url + path, method="GET", headers=self._headers)
        try:
            with self._opener.open(request, timeout=timeout) as response:
                data_lines: list[str] = []
                for raw in response:
                    line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                    if not line:
                        if data_lines:
                            try:
                                value = json.loads("\n".join(data_lines))
                            except json.JSONDecodeError:
                                value = None
                            if isinstance(value, dict):
                                yield value
                            data_lines.clear()
                        continue
                    if line.startswith("data:"):
                        data_lines.append(line[5:].lstrip())
        except urllib.error.HTTPError as exc:
            code = "OPENCODE_AUTH_REQUIRED" if exc.code in {401, 403} else "OPENCODE_CONNECTION_FAILED"
            raise OpenCodeError(code, "OpenCode event stream was rejected.") from exc
        except (OSError, urllib.error.URLError) as exc:
            raise OpenCodeError("OPENCODE_SERVER_UNAVAILABLE", "OpenCode event stream disconnected.") from exc


class GovernedToolBridge:
    """One-active-turn loopback endpoint used by the OpenCode MCP child."""

    def __init__(self, runtime: "OpenCodeRuntime"):
        self.runtime = runtime
        self.token = secrets.token_urlsafe(48)
        self._active: dict[str, Any] | None = None
        self._lock = threading.RLock()
        bridge = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_: Any) -> None:
                return

            def do_POST(self) -> None:
                if self.path != "/call" or not hmac.compare_digest(
                    self.headers.get("Authorization", ""), "Bearer " + bridge.token
                ):
                    self.send_response(404)
                    self.end_headers()
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 1_000_000:
                        raise ValueError("Request size rejected.")
                    body = json.loads(self.rfile.read(length).decode("utf-8"))
                    if not isinstance(body, dict) or set(body) != {"name", "arguments"} or not isinstance(body["arguments"], dict):
                        raise ValueError("Tool request envelope rejected.")
                    result = bridge.run(str(body["name"]), body["arguments"])
                    raw = json.dumps(result, ensure_ascii=False).encode("utf-8")
                    self.send_response(200)
                except Exception as exc:
                    raw = json.dumps({"status": "FAILED", "message": _safe_text(exc, 500)}).encode("utf-8")
                    self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, name="opencode-mne-mcp", daemon=True)
        self.thread.start()

    def bind(self, state: dict[str, Any]) -> None:
        with self._lock:
            if self._active is not None:
                raise OpenCodeError("OPENCODE_CONNECTION_FAILED", "Governed OpenCode tool bridge is already active.")
            self._active = state

    def unbind(self, turn_id: str) -> None:
        with self._lock:
            if self._active and self._active.get("gui_turn_id") == turn_id:
                self._active = None

    def config(self, relay_path: Path) -> dict[str, Any]:
        port = int(self.server.server_address[1])
        return {
            "type": "local",
            "command": [sys.executable, str(relay_path.resolve())],
            "environment": {
                "MNE_OPENCODE_MCP_URL": f"http://127.0.0.1:{port}/call",
                "MNE_OPENCODE_MCP_TOKEN": self.token,
            },
            "enabled": True,
        }

    def run(self, alias: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool_name = ALIASES.get(alias)
        if not tool_name:
            raise OpenCodeError("OPENCODE_CONNECTION_FAILED", "OpenCode requested a tool outside the governed allowlist.")
        with self._lock:
            state = deepcopy(self._active)
        if not state:
            raise OpenCodeError("OPENCODE_CONNECTION_FAILED", "Governed tool call is not bound to an active OpenCode turn.")
        broker = self.runtime.tool_broker
        call = broker.propose(
            thread_id=state["gui_thread_id"],
            turn_id=state["gui_turn_id"],
            tool_name=tool_name,
            arguments=arguments,
            permission_mode=state["permission_mode"],
        )
        preparation = tool_name in {"p10.prepare", "p10.prepare_critical", "owner_direct.prepare_write"}
        status = "AUTOMATIC_PREPARATION" if preparation else "AUTOMATIC_READ"
        category = "WRITE_RISK_PREPARATION" if preparation else ("OWNER_DIRECT_READ" if tool_name.startswith("owner_direct.") else ("P7_LIVE_READ" if tool_name == "mne.prepare_live_read" else ("WORKSPACE_READ" if tool_name.startswith("workspace.") else "EVIDENCE_AND_PLANNING")))
        target = arguments.get("target") or arguments.get("entity_id") or arguments.get("path") or "governed-scope"
        self.runtime.event_sink(
            state["gui_thread_id"],
            state["gui_turn_id"],
            "tool.proposed",
            {"tool_call_id": call["tool_call_id"], "tool_name": tool_name, "argument_digest": call["argument_digest"], "status": status, "operation_category": category, "target": _safe_text(target, 253)},
        )
        self.runtime.event_sink(
            state["gui_thread_id"], state["gui_turn_id"], "tool.started",
            {"tool_call_id": call["tool_call_id"], "tool_name": tool_name, "mode": status, "operation_category": category, "target": _safe_text(target, 253)},
        )
        try:
            if tool_name == "mne.prepare_live_read":
                result = broker.run_owner_autonomous_live_read(
                    arguments,
                    owner_session_digest=state["owner_session_digest"],
                    tool_call_id=call["tool_call_id"],
                )
                envelope = {"tool_call_id": call["tool_call_id"], "status": result.get("status", "COMPLETED"), "result": result}
            else:
                envelope = broker.invoke(call["tool_call_id"], owner_session_digest=state["owner_session_digest"])
            safe = _sanitize(envelope)
        except Exception as exc:
            safe = {"tool_call_id": call["tool_call_id"], "status": "FAILED", "message": _safe_text(exc)}
        self.runtime.event_sink(
            state["gui_thread_id"], state["gui_turn_id"], "tool.completed",
            {"tool_call_id": call["tool_call_id"], "tool_name": tool_name, "operation_category": category, "target": _safe_text(target, 253), "result": safe.get("result", safe)},
        )
        return safe

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.token = ""
        with self._lock:
            self._active = None


class OpenCodeRuntime:
    """Own one pure, loopback-only OpenCode server for MNE Brain."""

    _DENIED_TOOLS = {
        "bash": False,
        "edit": False,
        "write": False,
        "patch": False,
        "apply_patch": False,
        "task": False,
        "webfetch": False,
        "websearch": False,
        "question": False,
        "skill": False,
    }
    _CHILD_ENVIRONMENT = {
        "ALLUSERSPROFILE", "APPDATA", "BUN_INSTALL", "COMSPEC", "HOMEDRIVE", "HOMEPATH",
        "HTTPS_PROXY", "HTTP_PROXY", "LANG", "LOCALAPPDATA", "NO_PROXY", "NUMBER_OF_PROCESSORS",
        "OS", "PATH", "PATHEXT", "PROCESSOR_ARCHITECTURE", "PROGRAMDATA", "PROGRAMFILES",
        "PROGRAMFILES(X86)", "PROGRAMW6432", "SSL_CERT_DIR", "SSL_CERT_FILE", "SYSTEMDRIVE",
        "SYSTEMROOT", "TEMP", "TMP", "USERDOMAIN", "USERNAME", "USERPROFILE", "WINDIR",
        "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME",
    }

    def __init__(
        self,
        base_dir: Path,
        *,
        tool_broker: Any,
        event_sink: Callable[[str, str, str, dict[str, Any]], None],
        completion_sink: Callable[[str, str, str | None], None],
        failure_sink: Callable[[str, str], None],
        binary_finder: Callable[[], str | None] | None = None,
        process_factory: Callable[..., subprocess.Popen[Any]] | None = None,
        client: Any | None = None,
    ):
        self.base_dir = base_dir.resolve()
        self.tool_broker = tool_broker
        self.event_sink = event_sink
        self.completion_sink = completion_sink
        self.failure_sink = failure_sink
        self.binary_finder = binary_finder or self._find_binary
        self.process_factory = process_factory or subprocess.Popen
        self.custom_providers = CustomProviderStore(self.base_dir)
        self._client = client
        self._process: subprocess.Popen[Any] | None = None
        self._bridge: GovernedToolBridge | None = None
        self._port: int | None = None
        self._password = secrets.token_urlsafe(48)
        self._username = "mne-brain"
        self._status = "READY" if client is not None else "SERVER_UNAVAILABLE"
        self._version: str | None = None
        self._missing: list[str] = []
        self._providers: list[dict[str, Any]] = []
        self._models: list[dict[str, Any]] = []
        self._auth_methods: dict[str, list[dict[str, Any]]] = {}
        self._connected: set[str] = set()
        self._sessions: dict[str, dict[str, str]] = {}
        self._active: dict[str, dict[str, Any]] = {}
        self._cancelled: set[str] = set()
        self._turn_gate = threading.Lock()
        self._lock = threading.RLock()
        self._expected_stop = False
        self._restart_count = 0
        self._monitor: threading.Thread | None = None

    @staticmethod
    def _find_binary() -> str | None:
        discovered = shutil.which("opencode") or shutil.which("opencode.cmd") or shutil.which("opencode.exe")
        if not discovered:
            return None
        path = Path(discovered)
        if path.suffix.casefold() in {".cmd", ".ps1"}:
            executable = path.parent / "node_modules/opencode-ai/bin/opencode.exe"
            if executable.is_file():
                return str(executable)
        return discovered

    @staticmethod
    def _free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    @staticmethod
    def _parse_version(value: str) -> tuple[int, int, int] | None:
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", value)
        return tuple(int(item) for item in match.groups()) if match else None

    def _runtime_config(self) -> dict[str, Any]:
        if self._bridge is None:
            raise OpenCodeError("OPENCODE_SERVER_UNAVAILABLE", "Governed MCP bridge is unavailable.")
        return {
            "$schema": "https://opencode.ai/config.json",
            "permission": {
                "*": "deny",
                "read": "deny",
                "edit": "deny",
                "bash": "deny",
                "task": "deny",
                "external_directory": "deny",
                "webfetch": "deny",
                "websearch": "deny",
                "question": "deny",
                "skill": "deny",
                "mne_brain_*": "allow",
            },
            "mcp": {"mne_brain": self._bridge.config(self.base_dir / "core/tools/mcp_relay.py")},
            "provider": self.custom_providers.opencode_config(),
        }

    def _child_environment(self) -> dict[str, str]:
        """Build an allowlisted environment with explicitly named AI credentials only."""
        environment = {name: value for name, value in os.environ.items() if name.upper() in self._CHILD_ENVIRONMENT}
        references = {
            str(item.get("environment_ref"))
            for item in self.custom_providers.list()
            if item.get("environment_ref")
        }
        references.update(
            value.strip()
            for value in os.environ.get("OPENCODE_PROVIDER_ENV_REFS", "").split(",")
            if re.fullmatch(r"[A-Z][A-Z0-9_]{2,80}", value.strip())
        )
        for name in references:
            if name in os.environ:
                environment[name] = os.environ[name]
        return environment

    def _launch_process(self, binary: str) -> None:
        self._port = self._free_port()
        environment = self._child_environment()
        environment.update(
            {
                "OPENCODE_SERVER_PASSWORD": self._password,
                "OPENCODE_SERVER_USERNAME": self._username,
                "OPENCODE_CONFIG_CONTENT": json.dumps(self._runtime_config(), separators=(",", ":")),
            }
        )
        self._process = self.process_factory(
            [binary, "serve", "--hostname", "127.0.0.1", "--port", str(self._port), "--pure", "--log-level", "ERROR"],
            cwd=str(self.base_dir),
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self._client = OpenCodeHTTPClient(f"http://127.0.0.1:{self._port}", self._username, self._password)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                break
            try:
                health = self._client.request("GET", "/global/health", timeout=1)
                if isinstance(health, dict) and health.get("healthy") is True:
                    self._version = str(health.get("version") or self._version or "")
                    return
            except OpenCodeError:
                time.sleep(0.15)
        raise OpenCodeError("OPENCODE_SERVER_UNAVAILABLE", "OpenCode did not become ready on loopback.")

    def start(self) -> dict[str, Any]:
        with self._lock:
            if self._client is not None and (self._process is None or self._process.poll() is None):
                try:
                    self.refresh_catalog(start_process=False)
                    return self.readiness(start_process=False)
                except OpenCodeError:
                    if self._process is None:
                        raise
            self._status = "STARTING"
            self._missing = []
            binary = self.binary_finder()
            if not binary:
                self._status = "NOT_INSTALLED"
                self._missing = ["Install OpenCode and ensure `opencode` is available to the GUI server user."]
                return self.readiness(start_process=False)
            try:
                result = subprocess.run(
                    [binary, "--version"], cwd=str(self.base_dir), capture_output=True, text=True,
                    timeout=5, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                self._version = (result.stdout or "").strip()[:80]
            except (OSError, subprocess.SubprocessError):
                self._version = None
            parsed = self._parse_version(self._version or "")
            if parsed is None or parsed < OPENCODE_MINIMUM_VERSION:
                self._status = "VERSION_UNSUPPORTED"
                self._missing = ["OpenCode 1.0.0 or newer is required."]
                return self.readiness(start_process=False)
            self._expected_stop = False
            if self._bridge is None:
                self._bridge = GovernedToolBridge(self)
            try:
                self._launch_process(binary)
                self.refresh_catalog(start_process=False)
            except OpenCodeError:
                self._status = "SERVER_UNAVAILABLE"
                self._missing = ["The protected loopback OpenCode server could not be started."]
                self._terminate_process()
                return self.readiness(start_process=False)
            if self._monitor is None or not self._monitor.is_alive():
                self._monitor = threading.Thread(target=self._monitor_process, name="opencode-supervisor", daemon=True)
                self._monitor.start()
            return self.readiness(start_process=False)

    def _monitor_process(self) -> None:
        while True:
            with self._lock:
                process = self._process
                expected = self._expected_stop
            if process is None or expected:
                return
            process.wait()
            with self._lock:
                if self._expected_stop or process is not self._process:
                    return
                self._status = "SERVER_UNAVAILABLE"
            restarted = False
            for attempt in range(3):
                time.sleep(0.5 * (2**attempt))
                with self._lock:
                    if self._expected_stop:
                        return
                    binary = self.binary_finder()
                    if not binary:
                        break
                    try:
                        self._launch_process(binary)
                        self.refresh_catalog(start_process=False)
                        self._restart_count += 1
                        restarted = True
                        break
                    except OpenCodeError:
                        self._terminate_process()
            if not restarted:
                with self._lock:
                    self._status = "SERVER_UNAVAILABLE"
                for turn_id in list(self._active):
                    self.failure_sink(turn_id, "OPENCODE_SERVER_UNAVAILABLE")
                return

    def _terminate_process(self) -> None:
        process = self._process
        self._process = None
        self._client = None
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=5)
        except (OSError, subprocess.SubprocessError):
            try:
                process.kill()
            except OSError:
                pass

    def stop(self) -> None:
        with self._lock:
            self._expected_stop = True
            client = self._client
        if client is not None:
            try:
                client.request("POST", "/instance/dispose", {}, timeout=2)
            except OpenCodeError:
                pass
        with self._lock:
            self._terminate_process()
            if self._bridge is not None:
                self._bridge.stop()
                self._bridge = None
            self._status = "SERVER_UNAVAILABLE"
            self._sessions.clear()

    def restart(self) -> dict[str, Any]:
        if self._active:
            raise OpenCodeError("OPENCODE_CONNECTION_FAILED", "OpenCode cannot restart during an active turn.")
        self.stop()
        with self._lock:
            self._password = secrets.token_urlsafe(48)
            self._expected_stop = False
        return self.start()

    @staticmethod
    def _cost_classification(cost: Any) -> str:
        if not isinstance(cost, dict) or not isinstance(cost.get("input"), (int, float)) or not isinstance(cost.get("output"), (int, float)):
            return "UNKNOWN"
        numbers: list[float] = []

        def collect(value: Any) -> None:
            if isinstance(value, dict):
                for child in value.values():
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)
            elif isinstance(value, (int, float)):
                numbers.append(float(value))

        collect(cost)
        if not numbers:
            return "UNKNOWN"
        return "FREE" if all(value == 0 for value in numbers) else "PAID"

    def refresh_catalog(self, *, start_process: bool = True) -> dict[str, Any]:
        if self._client is None:
            if start_process:
                self.start()
            if self._client is None:
                raise OpenCodeError("OPENCODE_SERVER_UNAVAILABLE", "OpenCode server is unavailable.")
        provider_payload = self._client.request("GET", "/provider" + self._directory_query(), timeout=60)
        auth_payload = self._client.request("GET", "/provider/auth" + self._directory_query(), timeout=60)
        if not isinstance(provider_payload, dict) or not isinstance(provider_payload.get("all"), list) or not isinstance(auth_payload, dict):
            raise OpenCodeError("OPENCODE_CONNECTION_FAILED", "OpenCode returned an invalid provider catalog.")
        connected = {str(item) for item in provider_payload.get("connected", [])}
        custom_ids = {str(item.get("provider_id")) for item in self.custom_providers.list()}
        providers: list[dict[str, Any]] = []
        models: list[dict[str, Any]] = []
        methods: dict[str, list[dict[str, Any]]] = {}
        for provider in provider_payload["all"]:
            if not isinstance(provider, dict):
                continue
            provider_id = str(provider.get("id", ""))
            if not provider_id:
                continue
            raw_methods = auth_payload.get(provider_id, [])
            clean_methods = []
            if isinstance(raw_methods, list):
                for index, method in enumerate(raw_methods):
                    if not isinstance(method, dict) or method.get("type") not in {"api", "oauth"}:
                        continue
                    prompts = []
                    for prompt in method.get("prompts", []) if isinstance(method.get("prompts"), list) else []:
                        if isinstance(prompt, dict):
                            prompt_key = str(prompt.get("key", ""))[:100]
                            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,99}", prompt_key):
                                continue
                            clean_prompt: dict[str, Any] = {
                                "key": prompt_key,
                                "type": str(prompt.get("type", "text"))[:30],
                                "message": _safe_text(prompt.get("message") or prompt.get("label") or prompt_key, 300),
                                "required": prompt.get("required") is not False,
                            }
                            options = prompt.get("options")
                            if isinstance(options, list):
                                clean_options = []
                                for option in options[:100]:
                                    if isinstance(option, str):
                                        clean_options.append(_safe_text(option, 200))
                                    elif isinstance(option, dict) and (option.get("value") is not None or option.get("label") is not None):
                                        clean_options.append({
                                            "value": _safe_text(option.get("value") or option.get("label"), 200),
                                            "label": _safe_text(option.get("label") or option.get("value"), 200),
                                        })
                                clean_prompt["options"] = clean_options
                            prompts.append(clean_prompt)
                    clean_methods.append({"index": index, "type": method["type"], "label": _safe_text(method.get("label"), 160), "prompts": prompts})
            methods[provider_id] = clean_methods
            warnings = []
            if "anthropic" in (provider_id + " " + str(provider.get("name", ""))).casefold() and any(item["type"] == "oauth" for item in clean_methods):
                warnings.append("Claude Pro/Max subscription use through OpenCode may not be officially supported by Anthropic and is not guaranteed.")
            provider_models = provider.get("models") if isinstance(provider.get("models"), dict) else {}
            providers.append(
                {
                    "provider_id": provider_id,
                    "display_name": _safe_text(provider.get("name") or provider_id, 160),
                    "source": _safe_text(provider.get("source"), 40),
                    "environment_refs": [str(item)[:100] for item in provider.get("env", []) if isinstance(item, str)],
                    "connected": provider_id in connected,
                    "connection_status": "CONNECTED" if provider_id in connected else "NOT_CONNECTED",
                    "authentication_methods": clean_methods,
                    "model_count": len(provider_models),
                    "warnings": warnings,
                    "custom": provider_id in custom_ids,
                }
            )
            for model_id, model in provider_models.items():
                if not isinstance(model, dict):
                    continue
                capabilities = model.get("capabilities") if isinstance(model.get("capabilities"), dict) else {}
                limits = model.get("limit") if isinstance(model.get("limit"), dict) else {}
                status = str(model.get("status", "active")).upper()
                selection_id = provider_id + "/" + str(model_id)
                model_warnings = list(warnings)
                if status == "DEPRECATED":
                    model_warnings.append("OpenCode marks this model as deprecated.")
                models.append(
                    {
                        "selection_id": selection_id,
                        "provider_id": provider_id,
                        "model_id": str(model_id)[:300],
                        "display_name": _safe_text(model.get("name") or model_id, 200),
                        "cost_classification": self._cost_classification(model.get("cost")),
                        "context_limit": int(limits.get("context", 0) or 0),
                        "output_limit": int(limits.get("output", 0) or 0),
                        "tool_support": capabilities.get("toolcall") is True,
                        "reasoning": capabilities.get("reasoning") is True,
                        "availability": status,
                        "connected": provider_id in connected,
                        "connection_status": "CONNECTED" if provider_id in connected else "NOT_CONNECTED",
                        "warnings": model_warnings,
                    }
                )
        with self._lock:
            self._connected = connected
            self._providers = sorted(providers, key=lambda item: (not item["connected"], item["display_name"].casefold()))
            self._models = sorted(models, key=lambda item: (not item["connected"], item["cost_classification"] != "FREE", item["provider_id"], item["display_name"].casefold()))
            self._auth_methods = methods
            if not connected:
                self._status = "NO_CONNECTED_PROVIDER"
                self._missing = ["Connect at least one OpenCode provider."]
            elif not any(item["connected"] for item in models):
                self._status = "NO_MODELS"
                self._missing = ["Connected OpenCode providers exposed no models."]
            else:
                self._status = "READY"
                self._missing = []
        return self.catalog(start_process=False)

    def readiness(self, *, start_process: bool = False) -> dict[str, Any]:
        if start_process and self._client is None and self._status not in {"NOT_INSTALLED", "VERSION_UNSUPPORTED"}:
            return self.start()
        with self._lock:
            default = next((item["selection_id"] for item in self._models if item["connected"] and item["availability"] != "DEPRECATED"), None)
            return {
                "status": self._status,
                "provider_id": OPENCODE_PROVIDER_ID,
                "version": self._version,
                "bind_host": "127.0.0.1",
                "port": self._port,
                "basic_auth": "IN_MEMORY_ONLY",
                "native_shell": "DENIED",
                "native_edits": "DENIED",
                "external_directories": "DENIED",
                "native_subagents": "DENIED",
                "uncontrolled_mcp": "DENIED",
                "connected_provider_count": len(self._connected),
                "model_count": len(self._models),
                "default_model": default,
                "missing_prerequisites": list(self._missing),
                "restart_count": self._restart_count,
                "secrets_returned": False,
            }

    def catalog(self, *, start_process: bool = True) -> dict[str, Any]:
        if start_process and self._client is None:
            self.start()
        with self._lock:
            return {
                "providers": deepcopy(self._providers),
                "models": deepcopy(self._models),
                "connected_provider_ids": sorted(self._connected),
                "refreshed": bool(self._providers),
                "secrets_returned": False,
            }

    def _directory_query(self) -> str:
        return "?directory=" + urllib.parse.quote(str(self.base_dir), safe="")

    def _provider(self, provider_id: str) -> dict[str, Any]:
        item = next((value for value in self._providers if value["provider_id"] == provider_id), None)
        if item is None:
            raise OpenCodeError("OPENCODE_CONNECTION_FAILED", "OpenCode provider is unavailable.")
        return item

    def connect_api_key(self, provider_id: str, api_key: str) -> dict[str, Any]:
        self._provider(provider_id)
        if not isinstance(api_key, str) or not 1 <= len(api_key) <= 20_000:
            raise OpenCodeError("OPENCODE_AUTH_REQUIRED", "Provider API key is invalid.")
        assert self._client is not None
        self._client.request("PUT", "/auth/" + urllib.parse.quote(provider_id, safe=""), {"type": "api", "key": api_key}, timeout=30)
        self.refresh_catalog(start_process=False)
        return {"provider_id": provider_id, "status": "CONNECTED" if provider_id in self._connected else "AUTH_SAVED", "secrets_returned": False}

    def oauth_start(self, provider_id: str, method: int, inputs: dict[str, str] | None = None) -> dict[str, Any]:
        profile = self._provider(provider_id)
        methods = profile["authentication_methods"]
        selected = next((item for item in methods if item["index"] == method and item["type"] == "oauth"), None)
        if selected is None:
            raise OpenCodeError("OPENCODE_AUTH_REQUIRED", "Requested OAuth method is not reported by OpenCode.")
        assert self._client is not None
        body: dict[str, Any] = {"method": method}
        if inputs:
            body["inputs"] = {str(key)[:100]: str(value)[:1000] for key, value in inputs.items()}
        result = self._client.request(
            "POST",
            "/provider/" + urllib.parse.quote(provider_id, safe="") + "/oauth/authorize" + self._directory_query(),
            body,
            timeout=30,
        )
        if not isinstance(result, dict) or not str(result.get("url", "")).startswith("https://"):
            raise OpenCodeError("OPENCODE_CONNECTION_FAILED", "OpenCode returned an invalid authorization URL.")
        return {
            "provider_id": provider_id,
            "method": method,
            "authorization_url": str(result["url"]),
            "callback_method": str(result.get("method", "code")),
            "instructions": _safe_text(result.get("instructions"), 1000),
            "status": "WAITING",
            "secrets_returned": False,
        }

    def oauth_callback(self, provider_id: str, method: int, code: str | None = None) -> dict[str, Any]:
        self._provider(provider_id)
        body: dict[str, Any] = {"method": method}
        if code:
            body["code"] = str(code)[:10_000]
        assert self._client is not None
        self._client.request(
            "POST",
            "/provider/" + urllib.parse.quote(provider_id, safe="") + "/oauth/callback" + self._directory_query(),
            body,
            timeout=300,
        )
        self.refresh_catalog(start_process=False)
        return {"provider_id": provider_id, "status": "CONNECTED" if provider_id in self._connected else "FAILED", "secrets_returned": False}

    def disconnect(self, provider_id: str) -> dict[str, Any]:
        self._provider(provider_id)
        assert self._client is not None
        self._client.request("DELETE", "/auth/" + urllib.parse.quote(provider_id, safe=""), timeout=30)
        self.refresh_catalog(start_process=False)
        return {"provider_id": provider_id, "status": "DISCONNECTED", "secrets_returned": False}

    def test_provider(self, provider_id: str, model_id: str | None = None) -> dict[str, Any]:
        profile = self._provider(provider_id)
        selected = None
        if model_id:
            selected = next((item for item in self._models if item["provider_id"] == provider_id and item["model_id"] == model_id), None)
            if selected is None:
                raise OpenCodeError("OPENCODE_MODEL_REMOVED", "Selected OpenCode model is no longer available.")
        return {
            "provider_id": provider_id,
            "status": "CONNECTED" if profile["connected"] else "AUTH_REQUIRED",
            "model_available": selected is not None if model_id else profile["model_count"] > 0,
            "network_prompt_sent": False,
            "secrets_returned": False,
        }

    def upsert_custom_provider(self, profile: dict[str, Any]) -> dict[str, Any]:
        clean = self.custom_providers.upsert(profile)
        self.restart()
        return {"provider": clean, "status": "SAVED", "secrets_returned": False}

    def remove_custom_provider(self, provider_id: str) -> dict[str, Any]:
        removed = self.custom_providers.remove(provider_id)
        if removed:
            self.restart()
        return {"provider_id": provider_id, "status": "REMOVED" if removed else "NOT_FOUND", "secrets_returned": False}

    def _selected_model(self, selection_id: str) -> dict[str, Any]:
        item = next((value for value in self._models if value["selection_id"] == selection_id), None)
        if item is None or item["availability"] == "DEPRECATED":
            raise OpenCodeError("OPENCODE_MODEL_REMOVED", "Selected OpenCode model is no longer available. Choose another model.")
        if not item["connected"]:
            raise OpenCodeError("OPENCODE_AUTH_REQUIRED", "The selected OpenCode provider is not connected.")
        custom = next((value for value in self.custom_providers.list() if value.get("provider_id") == item["provider_id"]), None)
        if custom is not None:
            validate_endpoint(custom["base_url"], allow_loopback=custom.get("allow_loopback") is True)
        return item

    def _ensure_session(self, gui_thread_id: str, selection_id: str) -> str:
        existing = self._sessions.get(gui_thread_id)
        if existing:
            if existing["selection_id"] != selection_id:
                raise OpenCodeError("OPENCODE_MODEL_REMOVED", "OpenCode model cannot change inside a pinned conversation.")
            return existing["session_id"]
        model = self._selected_model(selection_id)
        assert self._client is not None
        session = self._client.request(
            "POST",
            "/session" + self._directory_query(),
            {
                "title": "MNE Brain " + gui_thread_id,
                "model": {"providerID": model["provider_id"], "id": model["model_id"]},
                "permission": [
                    {"permission": "*", "pattern": "*", "action": "deny"},
                    {"permission": "mne_brain_*", "pattern": "*", "action": "allow"},
                ],
            },
            timeout=20,
        )
        session_id = str(session.get("id", "")) if isinstance(session, dict) else ""
        if not session_id.startswith("ses"):
            raise OpenCodeError("OPENCODE_CONNECTION_FAILED", "OpenCode did not create a valid session.")
        self._sessions[gui_thread_id] = {"session_id": session_id, "selection_id": selection_id}
        return session_id

    @staticmethod
    def _instructions() -> str:
        return (
            "You are the OpenCode secondary engine inside MNE Brain. Use only mne_brain_* governed tools. "
            "Never request native shell, edit, write, patch, external-directory, subagent, web, or uncontrolled MCP access. "
            "Safe documented and approved reads may run automatically through MNE Brain. For any infrastructure change, "
            "prepare one complete immutable P10 package and stop for owner approval; never approve or execute it yourself. "
            "Report operational progress and evidence, not hidden chain-of-thought or private reasoning. Distinguish documented, "
            "live-verified, inferred, and unknown facts. Never expose credentials or raw sensitive provider content."
        )

    def start_turn(
        self,
        *,
        gui_thread_id: str,
        gui_turn_id: str,
        content: str,
        owner_session_digest: str,
        model_id: str,
        permission_mode: str,
        timeout_seconds: int = 600,
    ) -> None:
        worker = threading.Thread(
            target=self._run_turn,
            args=(gui_thread_id, gui_turn_id, content, owner_session_digest, model_id, permission_mode, timeout_seconds),
            name="opencode-" + gui_turn_id,
            daemon=True,
        )
        worker.start()

    def _run_turn(self, gui_thread_id: str, gui_turn_id: str, content: str, owner_digest: str, selection_id: str, permission_mode: str, timeout_seconds: int) -> None:
        with self._turn_gate:
            try:
                if gui_turn_id in self._cancelled:
                    raise OpenCodeError("OPENCODE_TURN_CANCELLED", "OpenCode turn was cancelled.")
                ready = self.start()
                if ready["status"] != "READY":
                    mapping = {
                        "NOT_INSTALLED": "OPENCODE_NOT_INSTALLED",
                        "VERSION_UNSUPPORTED": "OPENCODE_VERSION_UNSUPPORTED",
                        "NO_CONNECTED_PROVIDER": "OPENCODE_NO_CONNECTED_PROVIDER",
                        "NO_MODELS": "OPENCODE_NO_MODELS",
                    }
                    raise OpenCodeError(mapping.get(ready["status"], "OPENCODE_SERVER_UNAVAILABLE"), "OpenCode is not ready.")
                session_id = self._ensure_session(gui_thread_id, selection_id)
                model = self._selected_model(selection_id)
                state = {
                    "gui_thread_id": gui_thread_id,
                    "gui_turn_id": gui_turn_id,
                    "owner_session_digest": owner_digest,
                    "permission_mode": permission_mode,
                    "session_id": session_id,
                }
                with self._lock:
                    self._active[gui_turn_id] = state
                assert self._bridge is not None and self._client is not None
                self._bridge.bind(state)
                self.event_sink(gui_thread_id, gui_turn_id, "agent.progress", {"text": "OpenCode session is investigating through governed MNE tools."})
                path = "/session/" + urllib.parse.quote(session_id, safe="") + "/prompt_async" + self._directory_query()
                self._client.request(
                    "POST",
                    path,
                    {
                        "model": {"providerID": model["provider_id"], "modelID": model["model_id"]},
                        "system": self._instructions(),
                        "tools": self._DENIED_TOOLS,
                        "parts": [{"type": "text", "text": content}],
                    },
                    timeout=30,
                )
                deadline = time.monotonic() + max(1, min(timeout_seconds, 1800))
                idle = False
                reconnects = 0
                while time.monotonic() < deadline and not idle:
                    if gui_turn_id in self._cancelled:
                        raise OpenCodeError("OPENCODE_TURN_CANCELLED", "OpenCode turn was cancelled.")
                    try:
                        for event in self._client.events("/event" + self._directory_query(), timeout=30):
                            if gui_turn_id in self._cancelled:
                                raise OpenCodeError("OPENCODE_TURN_CANCELLED", "OpenCode turn was cancelled.")
                            properties = event.get("properties") if isinstance(event.get("properties"), dict) else {}
                            if properties.get("sessionID") != session_id:
                                continue
                            event_type = str(event.get("type", ""))
                            if event_type == "message.part.delta" and properties.get("field") == "text":
                                delta = str(properties.get("delta", ""))
                                if delta:
                                    self.event_sink(gui_thread_id, gui_turn_id, "answer.delta", {"text": delta})
                            elif event_type == "session.status":
                                status = properties.get("status") if isinstance(properties.get("status"), dict) else {}
                                if status.get("type") == "retry":
                                    message = _safe_text(status.get("message"), 300)
                                    self.event_sink(gui_thread_id, gui_turn_id, "agent.progress", {"text": "OpenCode provider retrying safely" + (": " + message if message else ".")})
                            elif event_type == "session.error":
                                raise self._event_error(properties.get("error"))
                            elif event_type == "session.idle":
                                idle = True
                                break
                        if not idle:
                            reconnects += 1
                    except OpenCodeError as exc:
                        if exc.code not in {"OPENCODE_SERVER_UNAVAILABLE", "OPENCODE_CONNECTION_FAILED"} or reconnects >= 5:
                            raise
                        reconnects += 1
                        time.sleep(min(reconnects, 3))
                    if not idle:
                        statuses = self._client.request("GET", "/session/status" + self._directory_query(), timeout=10)
                        current = statuses.get(session_id) if isinstance(statuses, dict) else None
                        if isinstance(current, dict) and current.get("type") == "idle":
                            idle = True
                if not idle:
                    raise OpenCodeError("OPENCODE_TIMEOUT", "OpenCode turn exceeded the governed timeout.")
                answer = self._final_answer(session_id)
                if not answer:
                    raise OpenCodeError("OPENCODE_EMPTY_RESPONSE", "OpenCode completed without a user-visible answer.")
                self.event_sink(gui_thread_id, gui_turn_id, "answer.final", {"text": answer})
                self.completion_sink(gui_thread_id, gui_turn_id, answer)
            except OpenCodeError as exc:
                readiness_status = {
                    "OPENCODE_AUTH_REQUIRED": "AUTH_REQUIRED",
                    "OPENCODE_MODEL_REMOVED": "MODEL_REMOVED",
                    "OPENCODE_RATE_LIMITED": "RATE_LIMITED",
                    "OPENCODE_SERVER_UNAVAILABLE": "SERVER_UNAVAILABLE",
                    "OPENCODE_CONNECTION_FAILED": "CONNECTION_FAILED",
                }.get(exc.code)
                if readiness_status:
                    with self._lock:
                        self._status = readiness_status
                self.failure_sink(gui_turn_id, exc.code)
            except Exception:
                self.failure_sink(gui_turn_id, "OPENCODE_CONNECTION_FAILED")
            finally:
                if self._bridge is not None:
                    self._bridge.unbind(gui_turn_id)
                with self._lock:
                    self._active.pop(gui_turn_id, None)
                    self._cancelled.discard(gui_turn_id)

    @staticmethod
    def _event_error(error: Any) -> OpenCodeError:
        text = json.dumps(_sanitize(error), ensure_ascii=False).casefold() if error is not None else ""
        if "rate" in text and "limit" in text:
            return OpenCodeError("OPENCODE_RATE_LIMITED", "OpenCode provider rate limit was reached.")
        if "auth" in text or "credential" in text or "unauthorized" in text:
            return OpenCodeError("OPENCODE_AUTH_REQUIRED", "OpenCode provider authentication is required.")
        if "abort" in text or "cancel" in text:
            return OpenCodeError("OPENCODE_TURN_CANCELLED", "OpenCode turn was cancelled.")
        return OpenCodeError("OPENCODE_CONNECTION_FAILED", "OpenCode provider request failed.")

    def _final_answer(self, session_id: str) -> str:
        assert self._client is not None
        items = self._client.request(
            "GET", "/session/" + urllib.parse.quote(session_id, safe="") + "/message" + self._directory_query(), timeout=20
        )
        if not isinstance(items, list):
            return ""
        for item in reversed(items):
            if not isinstance(item, dict):
                continue
            info = item.get("info") if isinstance(item.get("info"), dict) else {}
            if info.get("role") != "assistant":
                continue
            parts = item.get("parts") if isinstance(item.get("parts"), list) else []
            text = "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict) and part.get("type") == "text" and not part.get("ignored"))
            if text.strip():
                return text.strip()[:200_000]
        return ""

    def cancel(self, gui_turn_id: str) -> None:
        with self._lock:
            self._cancelled.add(gui_turn_id)
            state = self._active.get(gui_turn_id)
            client = self._client
        if state and client:
            try:
                client.request("POST", "/session/" + urllib.parse.quote(state["session_id"], safe="") + "/abort" + self._directory_query(), {}, timeout=5)
            except OpenCodeError:
                pass
