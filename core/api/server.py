#!/usr/bin/env python3
"""
MNE_Brain Release 2 — REST API Server (`core/api/server.py`)
Provides pure REST JSON API endpoints exposing MNE_Brain core engines to external clients and presentation GUI.
MANDATORY RULE: ZERO Business Logic in GUI. Presentation ONLY.
"""

import os
import sys
import json
import hashlib
import re
import socket
import threading
import time
import yaml
import jsonschema
import urllib.parse
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from typing import Dict, Any, List

# Add project root to sys.path
base_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(base_dir))

from core.entity.build_entity_index import EntityIndexBuilder
from core.connectors.registry import ConnectorRegistry
from core.transports.registry import TransportRegistry
from core.troubleshooting.engine import P8TroubleshootingEngine
from core.troubleshooting.p9_engine import P9DiagnosticEngine
from core.lifecycle.lifecycle_engine import KnowledgeLifecycleEngine
from core.incidents.case_manager import IncidentCaseManager
from core.incidents.intake import IncidentIntakeService
from core.incidents.workflow_governance import IncidentWorkflowGovernance
from core.llm.llm_adapter import LLMAdapter
from core.remediation.remediation_engine import RemediationEngine
from core.execution.p10_engine import OWNER_REFERENCE, P10ExecutionEngine, P10SafetyError
from core.execution.p10_readiness import P10ReadinessService
from core.infrastructure.coverage import InfrastructureCoverageService
from core.api.p10_local import P10LocalAPIContext
from core.api.security import OwnerCredentialVerifier, OwnerSessionError, OwnerSessionManager
from core.conversation.engine import ConversationEngine
from core.conversation.thread_store import ThreadStoreError
from core.codex.app_server import CODEX_PROVIDER_ID, CodexAppServerError
from core.opencode import OPENCODE_PROVIDER_ID, OpenCodeError
from core.opencode.custom_providers import CustomProviderError
from core.antigravity import ANTIGRAVITY_PROVIDER_ID, AntigravityCliError
from core.credentials import CredentialStore
from core.llm.external_authorization import ExternalAuthorizationError
from core.llm.gateway import ProviderGateway
from core.llm.registry import ProviderRegistry, ProviderRegistryError
from core.tools.broker import ToolBroker, ToolBrokerError
from core.runbooks.registry import RunbookRegistry
from core.observability.tracer import ObservabilityTracer
from integrations.n8n.webhook_listener import WebhookAlertListener

security_policy = yaml.safe_load((base_dir / "config/p11_security_policy.yaml").read_text(encoding="utf-8")) or {}
owner_policy = security_policy.get("owner_session", {})
credential_store = CredentialStore(base_dir)
owner_credentials = OwnerCredentialVerifier(
    username=credential_store.get(str(owner_policy.get("username_ref", "MNE_OWNER_USERNAME"))),
    password_hash=credential_store.get(str(owner_policy.get("password_hash_ref", "MNE_OWNER_PASSWORD_HASH"))),
)
owner_sessions = OwnerSessionManager(
    inactivity_seconds=int(owner_policy.get("inactivity_seconds", 900)),
    nonce_ttl_seconds=int(owner_policy.get("nonce_ttl_seconds", 300)),
    max_sessions=int(owner_policy.get("max_sessions", 8)),
    cookie_name=str(owner_policy.get("cookie_name", "mne_owner_session")),
    credential_verifier=owner_credentials,
    maximum_failures=int(owner_policy.get("maximum_failures", 5)),
    lockout_seconds=int(owner_policy.get("lockout_seconds", 300)),
)
provider_registry = ProviderRegistry(base_dir)
provider_gateway = ProviderGateway(
    base_dir,
    registry=provider_registry,
    credentials=credential_store,
    external_calls_enabled=bool(security_policy.get("execution", {}).get("external_provider_calls_enabled", False)),
)
tool_broker = ToolBroker(
    base_dir,
    p7_live_enabled=bool(security_policy.get("execution", {}).get("p7_live_reads_enabled", False)),
    p7_scoped_available=bool(security_policy.get("execution", {}).get("p7_owner_scoped_live_reads_available", False)),
    p10_execution_enabled=bool(security_policy.get("execution", {}).get("p10_writes_enabled", False)),
)
conversation_engine = ConversationEngine(
    base_dir,
    gateway=provider_gateway,
    tool_broker=tool_broker,
    auto_authorize_external_redacted_context=bool(
        security_policy.get("external_data", {}).get("auto_authorize_redacted_conversation", False)
    ),
)
p10_api = P10LocalAPIContext(tool_broker.p10)
p10_readiness = P10ReadinessService(base_dir)
owner_full_control = InfrastructureCoverageService(base_dir)


def _codex_readiness(*, start_process: bool = False) -> Dict[str, Any]:
    """Return a secret-free readiness summary for the presentation layer."""
    result = conversation_engine.codex.readiness(start_process=start_process)
    try:
        transport = TransportRegistry(base_dir=base_dir).public_status()
        bindings = transport.get("credential_bindings", {})
        result["p7"] = {
            "owner_scoped_available": tool_broker.p7_scoped_available,
            "globally_enabled": tool_broker.p7_live_enabled,
            "active_bindings": int(bindings.get("active_bindings", 0)),
            "identity_conflicts": (
                transport.get("identity_conflicts", 0)
                if isinstance(transport.get("identity_conflicts", 0), int)
                else len(transport.get("identity_conflicts", []))
            ),
        }
    except (OSError, ValueError, KeyError, yaml.YAMLError):
        result["p7"] = {"owner_scoped_available": tool_broker.p7_scoped_available, "status": "CONFIGURATION_ERROR"}
    try:
        p10 = p10_readiness.status()
        result["p10"] = {
            "execution_enabled": tool_broker.p10.execution_enabled,
            "status": p10.get("status", "UNKNOWN"),
            "platforms": [
                {
                    "platform": item.get("platform"),
                    "live_status": item.get("live_status"),
                    "write_credentials": item.get("write_credentials"),
                }
                for item in p10.get("platforms", [])
            ],
        }
    except (OSError, ValueError, KeyError, yaml.YAMLError, jsonschema.ValidationError):
        result["p10"] = {"execution_enabled": tool_broker.p10.execution_enabled, "status": "CONFIGURATION_ERROR"}
    result["fallback_provider_id"] = "prv_local_deterministic"
    result["fallback_label"] = "Limited deterministic fallback"
    return result


def _opencode_readiness(*, start_process: bool = False) -> Dict[str, Any]:
    """Return a secret-free OpenCode server/provider readiness summary."""
    result = conversation_engine.opencode.readiness(start_process=start_process)
    result["p7"] = {"owner_scoped_available": tool_broker.p7_scoped_available, "globally_enabled": tool_broker.p7_live_enabled}
    result["p10"] = {"execution_enabled": tool_broker.p10.execution_enabled, "writes_require_exact_approval": True}
    return result


def _antigravity_readiness(*, start_process: bool = False) -> Dict[str, Any]:
    """Return a secret-free Antigravity CLI readiness summary."""
    result = conversation_engine.antigravity.readiness(start_process=start_process)
    result["p7"] = {"owner_scoped_available": tool_broker.p7_scoped_available, "globally_enabled": tool_broker.p7_live_enabled}
    result["p10"] = {"execution_enabled": tool_broker.p10.execution_enabled, "writes_require_exact_approval": True}
    result["unrestricted_read"] = True
    result["write_governance"] = "RISK_AND_ROLLBACK_REVIEW_REQUIRED"
    return result


def _engine_catalog(*, start_process: bool = False) -> Dict[str, Any]:
    codex = _codex_readiness(start_process=start_process)
    opencode = _opencode_readiness(start_process=start_process)
    opencode_catalog = conversation_engine.opencode.catalog(start_process=False)
    antigravity = _antigravity_readiness(start_process=start_process)
    return {
        "engines": [
            {"engine_id": "codex", "provider_id": CODEX_PROVIDER_ID, "label": "Codex App Server", "authentication": "ChatGPT session", "status": codex["status"], "models": [{"id": "codex-account-default", "label": "ChatGPT account default"}], "default_model": "codex-account-default", "details": codex},
            {"engine_id": "opencode", "provider_id": OPENCODE_PROVIDER_ID, "label": "OpenCode", "authentication": "Dynamic provider connection", "status": opencode["status"], "models": [{"id": item["selection_id"], "label": f"{item['display_name']} · {item['provider_id']} · {item['cost_classification']}", **item} for item in opencode_catalog["models"] if item["connected"]], "default_model": opencode["default_model"], "details": opencode},
            {"engine_id": "antigravity", "provider_id": ANTIGRAVITY_PROVIDER_ID, "label": "Antigravity CLI (1.1.26)", "authentication": "Google AI session", "status": antigravity["status"], "models": antigravity["models"], "default_model": antigravity["default_model"], "details": antigravity},
        ],
        "switch_policy": "PINNED_PER_CONVERSATION_AFTER_FIRST_TURN",
        "silent_fallback": False,
        "secrets_returned": False,
    }


class BoundedThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Concurrent SSE-capable server with a hard worker bound."""

    daemon_threads = True
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def __init__(self, server_address, handler_class, *, max_workers: int = 16):
        self._worker_slots = threading.BoundedSemaphore(max(1, max_workers))
        super().__init__(server_address, handler_class)

    def get_request(self):
        request, client_address = super().get_request()
        request.settimeout(float(security_policy.get("http", {}).get("request_timeout_seconds", 30)))
        return request, client_address

    def process_request(self, request, client_address):
        if not self._worker_slots.acquire(blocking=False):
            try:
                request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\nContent-Length: 0\r\n\r\n")
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._worker_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._worker_slots.release()

class MNEBrainAPIHandler(BaseHTTPRequestHandler):
    gui_dir = base_dir / "gui"
    server_version = "MNEBrainP11/2"
    protocol_version = "HTTP/1.0"

    def _resolve_gui_asset(self, request_path: str) -> Path | None:
        """Resolve a same-directory static asset and reject traversal or directories."""
        gui_root = self.gui_dir.resolve()
        decoded_path = urllib.parse.unquote(request_path)
        relative_path = decoded_path.lstrip("/") or "index.html"
        candidate = (gui_root / relative_path).resolve()
        try:
            candidate.relative_to(gui_root)
        except ValueError:
            return None
        return candidate if candidate.is_file() else None

    def _set_headers(self, status_code: int = 200, content_type: str = "application/json", *, extra_headers: Dict[str, str] | None = None, content_length: int | None = None):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        if content_length is not None:
            self.send_header("Content-Length", str(content_length))
        self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()

    def do_OPTIONS(self):
        if not owner_sessions.is_loopback(self._client_host()) or not owner_sessions.same_origin_loopback(self.headers.get("Host"), self.headers.get("Origin")):
            self._json_response(403, {"error": "Same-origin loopback request required."})
            return
        self._set_headers(204, content_length=0)

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        max_bytes = int(security_policy.get("http", {}).get("max_request_bytes", 1048576))
        if length < 0 or length > max_bytes:
            raise ValueError("Request body size rejected.")
        if not length:
            return {}
        raw_body = self.rfile.read(length).decode("utf-8")
        body = json.loads(raw_body)
        if not isinstance(body, dict):
            raise ValueError("JSON request body must be an object.")
        return body

    def _client_host(self) -> str:
        return self.client_address[0] if self.client_address else ""

    def _json_response(self, status_code: int, payload: Any, *, extra_headers: Dict[str, str] | None = None) -> None:
        raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        self._set_headers(status_code, "application/json; charset=utf-8", extra_headers=extra_headers, content_length=len(raw))
        self.wfile.write(raw)

    def _require_owner(self):
        return owner_sessions.require(client_host=self._client_host(), host_header=self.headers.get("Host"), origin_header=self.headers.get("Origin"), cookie_header=self.headers.get("Cookie"))

    def _authorize_mutation(self, body: Dict[str, Any]):
        return owner_sessions.authorize_mutation(
            client_host=self._client_host(), host_header=self.headers.get("Host"), origin_header=self.headers.get("Origin"),
            cookie_header=self.headers.get("Cookie"), csrf_token=self.headers.get("X-CSRF-Token"), nonce=body.get("request_nonce"),
        )

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        params = urllib.parse.parse_qs(parsed_url.query)

        # Serve only files that resolve inside gui/. Business and secret files are never static assets.
        if not path.startswith("/api"):
            file_path = self._resolve_gui_asset(path)

            if file_path is not None:
                ext = file_path.suffix.lower()
                ct = "text/html" if ext == ".html" else ("application/javascript" if ext in [".js", ".mjs"] else ("text/css" if ext == ".css" else "text/plain"))
                try:
                    raw = file_path.read_bytes()
                    self._set_headers(200, ct, content_length=len(raw))
                    self.wfile.write(raw)
                    return
                except Exception:
                    pass

        # REST API Endpoints
        if path == "/api/v2/session":
            try:
                session = self._require_owner()
                self._json_response(200, owner_sessions.describe(session))
            except OwnerSessionError as exc:
                self._json_response(401, {
                    "error": str(exc),
                    "code": "AUTHENTICATION_REQUIRED",
                    "owner_credentials_configured": owner_credentials.configured,
                    "local_interface_only": True,
                })
            return
        if path.startswith("/api"):
            try:
                self._require_owner()
            except OwnerSessionError as exc:
                self._json_response(401, {"error": str(exc), "code": "AUTHENTICATION_REQUIRED"})
                return
        if path.startswith("/api/v2/"):
            try:
                self._handle_v2_get(path, params)
            except (ThreadStoreError, ProviderRegistryError, ToolBrokerError, OpenCodeError, CustomProviderError, AntigravityCliError, ValueError, KeyError) as exc:
                self._json_response(404, {"error": str(exc)})
            return

        if path == "/api/status" or path == "/api/dashboard":
            self._handle_dashboard()
        elif path == "/api/devices":
            self._handle_devices(params)
        elif path == "/api/knowledge":
            self._handle_knowledge(params)
        elif path == "/api/investigations":
            self._handle_investigations(params)
        elif path == "/api/actions":
            self._handle_actions(params)
        elif path == "/api/automation":
            self._handle_automation()
        elif path == "/api/logs":
            self._handle_logs(params)
        elif path == "/api/settings":
            self._handle_settings_get()
        elif path.startswith("/api/oauth/chatgpt") or path == "/auth/callback":
            self._json_response(410, {"status": "QUARANTINED", "error": "ChatGPT OAuth is disabled; use a server-side OpenAI Platform credential reference."})
        elif path == "/api/search":
            self._handle_search(params)
        elif path == "/api/incidents/workflow/status":
            self._handle_incident_workflow_status(params)
        elif path == "/api/runbooks":
            self._handle_runbooks(params)
        elif path == "/api/connectors":
            self._handle_connectors(params)
        elif path == "/api/transports":
            self._handle_transports(params)
        elif path == "/api/troubleshooting/p8/status":
            self._handle_p8_status()
        elif path == "/api/troubleshooting/p9/status":
            self._handle_p9_status()
        elif path == "/api/p10/session":
            self._handle_p10_session()
        elif path == "/api/p10/operations":
            self._handle_p10_operations()
        elif path == "/api/p10/readiness":
            self._handle_p10_readiness()
        elif path.startswith("/api/p10/plans/"):
            self._handle_p10_plan_get(path.rsplit("/", 1)[-1])
        elif path.startswith("/api/p10/results/"):
            self._handle_p10_result_get(path.rsplit("/", 1)[-1])
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": f"Endpoint {path} not found"}).encode("utf-8"))

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        if path == "/api/v2/login":
            try:
                body = self._read_json_body()
                if set(body) != {"username", "password"}:
                    raise ValueError("Exact owner username and password are required.")
                payload, cookie = owner_sessions.login(
                    username=body["username"], password=body["password"],
                    client_host=self._client_host(), host_header=self.headers.get("Host"), origin_header=self.headers.get("Origin"),
                )
                self._json_response(200, payload, extra_headers={"Set-Cookie": cookie})
            except ValueError as exc:
                self._json_response(400, {"error": str(exc)})
            except OwnerSessionError as exc:
                self._json_response(401, {"error": str(exc), "code": "OWNER_LOGIN_FAILED"})
            return
        try:
            body = self._read_json_body()
            owner_session = self._authorize_mutation(body)
        except (ValueError, json.JSONDecodeError) as exc:
            self._json_response(400, {"error": str(exc)})
            return
        except OwnerSessionError as exc:
            self._json_response(403, {"error": str(exc)})
            return

        if path.startswith("/api/v2/"):
            try:
                if path == "/api/v2/logout":
                    cookie = owner_sessions.logout(cookie_header=self.headers.get("Cookie"))
                    self._json_response(200, {"status": "SIGNED_OUT"}, extra_headers={"Set-Cookie": cookie})
                    return
                self._handle_v2_post(path, body, owner_session)
            except (ThreadStoreError, ProviderRegistryError, ExternalAuthorizationError, ToolBrokerError, P10SafetyError, CodexAppServerError, OpenCodeError, CustomProviderError, AntigravityCliError, ValueError, KeyError, jsonschema.ValidationError) as exc:
                self._json_response(409, {"error": str(exc)})
            return

        if path == "/api/chat":
            self._handle_chat(body)
        elif path == "/api/incidents/intake":
            self._handle_incident_intake(body)
        elif path == "/api/actions/execute":
            self._handle_action_execute(body)
        elif path == "/api/knowledge/promote":
            self._handle_knowledge_promote(body)
        elif path == "/api/automation/trigger":
            self._handle_automation_trigger(body)
        elif path.startswith("/api/oauth/chatgpt"):
            self._json_response(410, {"status": "QUARANTINED", "error": "ChatGPT OAuth is disabled."})
        elif path == "/api/settings":
            self._handle_settings_post(body)
        elif path == "/api/settings/auto":
            self._handle_settings_auto()
        elif path == "/api/troubleshooting/p8/plan":
            self._handle_p8_plan(body)
        elif path == "/api/troubleshooting/p9/plan":
            self._handle_p9_plan(body)
        elif path == "/api/p10/plans/prepare":
            self._handle_p10_prepare(body)
        elif path == "/api/p10/plans/prepare-critical":
            self._handle_p10_prepare_critical(body)
        elif path.startswith("/api/p10/plans/") and path.endswith("/approve"):
            self._handle_p10_approve(path.split("/")[-2], body)
        elif path.startswith("/api/p10/plans/") and path.endswith("/execute"):
            self._handle_p10_execute(path.split("/")[-2], body)
        elif path.startswith("/api/p10/plans/") and path.endswith("/rollback/prepare"):
            self._handle_p10_rollback_prepare(path.split("/")[-3], body)
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": f"Endpoint {path} not found"}).encode("utf-8"))

    # Handler Implementation Methods
    def _handle_v2_get(self, path: str, params: Dict[str, Any]) -> None:
        if path == "/api/v2/threads":
            query = (params.get("search") or [""])[0]
            self._json_response(200, {"threads": conversation_engine.store.list_threads(query), "retention": "IN_MEMORY_ONLY"})
            return
        match = re.fullmatch(r"/api/v2/threads/(thr_[A-Za-z0-9_-]{16,64})", path)
        if match:
            self._json_response(200, conversation_engine.store.get_thread(match.group(1)))
            return
        match = re.fullmatch(r"/api/v2/threads/(thr_[A-Za-z0-9_-]{16,64})/export", path)
        if match:
            self._json_response(200, conversation_engine.store.export_thread(match.group(1)))
            return
        match = re.fullmatch(r"/api/v2/diagnostics/(diag_[A-Za-z0-9_-]{16,64})", path)
        if match:
            self._json_response(200, conversation_engine.diagnostics.get(match.group(1)))
            return
        match = re.fullmatch(r"/api/v2/turns/(trn_[A-Za-z0-9_-]{16,64})/events", path)
        if match:
            self._stream_turn_events(match.group(1))
            return
        if path == "/api/v2/providers":
            profiles = provider_registry.list_profiles(include_disabled=True)
            for profile in profiles:
                ref = profile.get("credential_ref")
                profile["credential_status"] = credential_store.status(ref)["status"] if ref else "NOT_REQUIRED"
            self._json_response(200, {"profiles": profiles, "secrets_returned": False})
            return
        if path == "/api/v2/engines":
            self._json_response(200, _engine_catalog(start_process=True))
            return
        if path == "/api/v2/tools":
            self._json_response(200, {"tools": tool_broker.registry.list()})
            return
        if path == "/api/v2/owner-full-control/status":
            self._json_response(200, owner_full_control.status())
            return
        if path == "/api/v2/codex/readiness":
            self._json_response(200, _codex_readiness(start_process=True))
            return
        if path == "/api/v2/opencode/readiness":
            self._json_response(200, _opencode_readiness(start_process=True))
            return
        if path == "/api/v2/opencode/providers":
            conversation_engine.opencode.refresh_catalog(start_process=True)
            self._json_response(200, conversation_engine.opencode.catalog(start_process=False))
            return
        if path == "/api/v2/antigravity/readiness":
            self._json_response(200, _antigravity_readiness(start_process=True))
            return
        if path == "/api/v2/antigravity/models":
            self._json_response(200, conversation_engine.antigravity.models())
            return
        if path == "/api/v2/settings":
            self._json_response(200, {
                "permission_mode": "OWNER_DIRECT",
                "owner_direct": {"enabled": True, "read_identity_mode": "COLLECT_UNVERIFIED", "write_confirmation": "FINAL_UI_CONFIRMATION_ONLY"},
                "bind_host": security_policy.get("bind_host", "127.0.0.1"),
                "external_provider_calls_enabled": provider_gateway.external_calls_enabled,
                "auto_authorize_redacted_conversation": conversation_engine.auto_authorize_external_redacted_context,
                "explicit_authorization_required_for_live_evidence": bool(security_policy.get("external_data", {}).get("explicit_authorization_required_for_live_evidence", True)),
                "p7_live_reads_enabled": tool_broker.p7_live_enabled,
                "p7_owner_scoped_live_reads_available": tool_broker.p7_scoped_available,
                "p10_writes_enabled": tool_broker.p10.execution_enabled,
                "credential_storage": "KEYRING_PREFERRED_ENV_FALLBACK",
                "secrets_returned": False,
                "codex": _codex_readiness(start_process=True),
                "opencode": _opencode_readiness(start_process=True),
                "antigravity": _antigravity_readiness(start_process=True),
            })
            return
        raise ThreadStoreError("P11 endpoint not found.")

    def _stream_turn_events(self, turn_id: str) -> None:
        terminal_types = {"turn.completed", "turn.cancelled", "turn.failed"}
        terminal_statuses = {"COMPLETED", "CANCELLED", "FAILED"}
        last_event_id = self.headers.get("Last-Event-ID")
        heartbeat = float(security_policy.get("http", {}).get("sse_heartbeat_seconds", 15))
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        # One response remains open for the full turn, then closes cleanly
        # after its terminal event so clients never enter reconnect polling.
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            while True:
                events = conversation_engine.events.list_after(turn_id, last_event_id)
                if not events:
                    turn = conversation_engine.store.get_turn(turn_id)
                    if turn["status"] in terminal_statuses:
                        return
                    events = conversation_engine.events.wait_after(turn_id, last_event_id, timeout=heartbeat)
                if not events:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
                    continue
                for event in events:
                    self.wfile.write(conversation_engine.events.encode_sse(event))
                    self.wfile.flush()
                    last_event_id = event["event_id"]
                    if event["event_type"] in terminal_types:
                        return
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, socket.timeout):
            return

    def _handle_v2_post(self, path: str, body: Dict[str, Any], owner_session) -> None:
        payload = {key: value for key, value in body.items() if key != "request_nonce"}
        if path == "/api/v2/threads":
            allowed = {"title", "provider_id", "engine_id", "model_id", "permission_mode"}
            if set(payload).difference(allowed):
                raise ValueError("Unknown thread fields rejected.")
            codex_ready = conversation_engine.codex.readiness(start_process=True)["status"] == "READY"
            antigravity_ready = conversation_engine.antigravity.readiness(start_process=True)["status"] == "READY"
            default_engine = "codex" if codex_ready else ("antigravity" if antigravity_ready else "opencode")
            requested_engine = str(payload.get("engine_id", default_engine))
            engine_providers = {"codex": CODEX_PROVIDER_ID, "opencode": OPENCODE_PROVIDER_ID, "antigravity": ANTIGRAVITY_PROVIDER_ID}
            if requested_engine not in engine_providers:
                raise ValueError("Only Codex App Server, OpenCode, and Antigravity CLI are selectable AI engines.")
            provider_id = str(payload.get("provider_id", engine_providers[requested_engine]))
            profile = provider_registry.get(provider_id)
            selected_model = str(payload.get("model_id") or profile["model_id"])
            if requested_engine == "opencode":
                ready = conversation_engine.opencode.readiness(start_process=True)
                selected_model = str(payload.get("model_id") or ready.get("default_model") or "select-model")
                if selected_model != "select-model":
                    conversation_engine.opencode._selected_model(selected_model)
            elif requested_engine == "antigravity":
                ready = conversation_engine.antigravity.readiness(start_process=True)
                selected_model = str(payload.get("model_id") or ready.get("default_model") or "gemini-3.8-flash-high")
            item = conversation_engine.create_thread(
                title=str(payload.get("title", "New conversation")),
                provider_id=provider_id,
                engine_id=requested_engine,
                model_id=selected_model,
                permission_mode=str(payload.get("permission_mode", "OWNER_DIRECT")),
            )
            self._json_response(201, item)
            return
        if path == "/api/v2/threads/import":
            serialized = json.dumps(payload.get("conversation"), ensure_ascii=False)
            if len(serialized.encode("utf-8")) > 2_000_000:
                raise ValueError("Conversation import exceeds the safe size limit.")
            self._json_response(201, conversation_engine.import_thread(payload["conversation"]))
            return
        match = re.fullmatch(r"/api/v2/threads/(thr_[A-Za-z0-9_-]{16,64})/turns", path)
        if match:
            if not isinstance(payload.get("content"), str) or not payload["content"].strip():
                raise ValueError("Turn content is required.")
            item = conversation_engine.start_turn(match.group(1), content=payload["content"], external_authorization_id=payload.get("external_authorization_id"), evidence=payload.get("evidence", []), owner_session_digest=owner_sessions.digest(owner_session), run_async=True)
            self._json_response(202, item)
            return
        match = re.fullmatch(r"/api/v2/threads/(thr_[A-Za-z0-9_-]{16,64})/external-authorizations", path)
        if match:
            item = conversation_engine.prepare_external_authorization(
                match.group(1), prompt=payload["prompt"], evidence_context=payload.get("evidence_context", []),
                evidence_sources=payload.get("evidence_sources", []), data_classification=payload.get("data_classification", "INTERNAL_REDACTED"),
                includes_live_evidence=payload.get("includes_live_evidence") is True,
            )
            self._json_response(201, item)
            return
        match = re.fullmatch(r"/api/v2/threads/(thr_[A-Za-z0-9_-]{16,64})/provider", path)
        if match:
            provider_registry.get(payload["provider_id"])
            self._json_response(200, conversation_engine.store.switch_provider(match.group(1), payload["provider_id"]))
            return
        match = re.fullmatch(r"/api/v2/threads/(thr_[A-Za-z0-9_-]{16,64})/engine", path)
        if match:
            engine_id = str(payload["engine_id"])
            provider_id = {"codex": CODEX_PROVIDER_ID, "opencode": OPENCODE_PROVIDER_ID, "antigravity": ANTIGRAVITY_PROVIDER_ID}.get(engine_id)
            if not provider_id:
                raise ValueError("Only Codex App Server, OpenCode, and Antigravity CLI are selectable AI engines.")
            profile = provider_registry.get(provider_id)
            model_id = str(payload.get("model_id", profile["model_id"]))
            if engine_id == "opencode":
                conversation_engine.opencode.refresh_catalog(start_process=True)
                conversation_engine.opencode._selected_model(model_id)
                current = conversation_engine.store.get_thread(match.group(1), include_items=False)
                if current["turn_ids"]:
                    available = {item["selection_id"] for item in conversation_engine.opencode.catalog(start_process=False)["models"] if item["connected"] and item["availability"] != "DEPRECATED"}
                    if current["model_id"] in available:
                        raise ThreadStoreError("Engine and model are pinned after the first turn. Create a new conversation to switch models.")
                    self._json_response(200, conversation_engine.store.recover_unavailable_opencode_model(match.group(1), model_id))
                    return
            elif engine_id == "antigravity":
                current = conversation_engine.store.get_thread(match.group(1), include_items=False)
                if current["turn_ids"]:
                    available = {item["id"] for item in conversation_engine.antigravity.models()["models"]}
                    if current["model_id"] in available:
                        raise ThreadStoreError("Engine and model are pinned after the first turn. Create a new conversation to switch models.")
            self._json_response(200, conversation_engine.store.pin_engine(match.group(1), provider_id=provider_id, engine_id=engine_id, model_id=model_id))
            return
        match = re.fullmatch(r"/api/v2/threads/(thr_[A-Za-z0-9_-]{16,64})/permission", path)
        if match:
            self._json_response(200, conversation_engine.store.set_permission_mode(match.group(1), payload["permission_mode"]))
            return
        match = re.fullmatch(r"/api/v2/turns/(trn_[A-Za-z0-9_-]{16,64})/cancel", path)
        if match:
            self._json_response(202, conversation_engine.cancel(match.group(1)))
            return
        if path == "/api/v2/providers":
            self._json_response(201, provider_registry.add_profile(payload["profile"]))
            return
        match = re.fullmatch(r"/api/v2/providers/(prv_[A-Za-z0-9_-]{3,64})/(enable|disable|test|connect)", path)
        if match:
            provider_id, action = match.groups()
            if provider_id == CODEX_PROVIDER_ID and action in {"test", "connect"}:
                result = conversation_engine.codex.readiness(start_process=action == "connect")
                result.update({"provider_id": provider_id, "network_attempted": False, "credential_status": "CHATGPT_SESSION", "secrets_returned": False})
            elif provider_id == OPENCODE_PROVIDER_ID and action in {"test", "connect"}:
                result = conversation_engine.opencode.readiness(start_process=True)
                result.update({"provider_id": provider_id, "network_attempted": False, "credential_status": "MANAGED_BY_OPENCODE", "secrets_returned": False})
            elif provider_id == ANTIGRAVITY_PROVIDER_ID and action in {"test", "connect"}:
                result = conversation_engine.antigravity.readiness(start_process=True)
                result.update({"provider_id": provider_id, "network_attempted": False, "credential_status": "LOCAL_CLI_SESSION", "secrets_returned": False})
            elif action == "test":
                profile = provider_registry.get(provider_id, require_enabled=False)
                ref = profile.get("credential_ref")
                credential_status = credential_store.status(ref)["status"] if ref else "NOT_REQUIRED"
                result = {"provider_id": provider_id, "status": "CONFIG_VALID", "credential_status": credential_status, "model_id": profile["model_id"], "network_attempted": False, "secrets_returned": False}
            elif action == "connect":
                profile = provider_registry.get(provider_id)
                events = list(provider_gateway.stream(provider_id, [{"role": "user", "content": "hello"}]))
                failure = next((event.payload for event in events if event.event_type == "failed"), None)
                completed = any(event.event_type == "completed" for event in events)
                text_received = any(event.event_type == "text_delta" and event.payload.get("text") for event in events)
                if failure:
                    result = {"provider_id": provider_id, "status": "CONNECTION_FAILED", "code": failure["code"], "message": failure["message"], "retryable": failure["retryable"], "network_attempted": failure["code"] != "EXTERNAL_CALLS_DISABLED", "secrets_returned": False}
                elif completed and text_received:
                    result = {"provider_id": provider_id, "status": "NETWORK_VALID", "model_id": profile["model_id"], "credential_status": "VALID", "network_attempted": True, "streaming_validated": True, "secrets_returned": False}
                else:
                    result = {"provider_id": provider_id, "status": "CONNECTION_FAILED", "code": "PROVIDER_STREAM_INCOMPLETE", "message": "The provider stream ended before completion.", "retryable": True, "network_attempted": True, "secrets_returned": False}
            else:
                result = provider_registry.set_enabled(provider_id, action == "enable")
            self._json_response(200, result)
            return
        match = re.fullmatch(r"/api/v2/codex/approvals/(cappr_[A-Za-z0-9_-]{16,64})/(approve|deny)", path)
        if match:
            approval_id, decision = match.groups()
            item = conversation_engine.codex.decide_approval(
                approval_id,
                phrase=payload.get("approval_phrase"),
                owner_session_digest=owner_sessions.digest(owner_session),
                approve=decision == "approve",
            )
            self._json_response(200, item)
            return
        if path == "/api/v2/opencode/providers/refresh":
            self._json_response(200, conversation_engine.opencode.refresh_catalog(start_process=True))
            return
        if path == "/api/v2/opencode/providers/connect-api":
            provider_id = str(payload.get("provider_id", ""))
            api_key = payload.pop("api_key", None)
            body.pop("api_key", None)
            try:
                result = conversation_engine.opencode.connect_api_key(provider_id, api_key)
            finally:
                api_key = None
            self._json_response(200, result)
            return
        if path == "/api/v2/opencode/providers/oauth/start":
            inputs = payload.pop("inputs", None)
            body.pop("inputs", None)
            try:
                result = conversation_engine.opencode.oauth_start(str(payload.get("provider_id", "")), int(payload.get("method", -1)), inputs)
            finally:
                inputs = None
            self._json_response(200, result)
            return
        if path == "/api/v2/opencode/providers/oauth/callback":
            code = payload.pop("code", None)
            body.pop("code", None)
            try:
                result = conversation_engine.opencode.oauth_callback(str(payload.get("provider_id", "")), int(payload.get("method", -1)), code)
            finally:
                code = None
            self._json_response(200, result)
            return
        if path == "/api/v2/opencode/providers/disconnect":
            self._json_response(200, conversation_engine.opencode.disconnect(str(payload.get("provider_id", ""))))
            return
        if path == "/api/v2/opencode/providers/test":
            self._json_response(200, conversation_engine.opencode.test_provider(str(payload.get("provider_id", "")), payload.get("model_id")))
            return
        if path == "/api/v2/opencode/custom-providers/save":
            self._json_response(200, conversation_engine.opencode.upsert_custom_provider(payload.get("provider")))
            return
        if path == "/api/v2/opencode/custom-providers/remove":
            self._json_response(200, conversation_engine.opencode.remove_custom_provider(str(payload.get("provider_id", ""))))
            return
        if path == "/api/v2/opencode/restart":
            self._json_response(200, conversation_engine.opencode.restart())
            return
        match = re.fullmatch(r"/api/v2/credentials/([A-Z][A-Z0-9_]{2,80})", path)
        if match:
            ref = match.group(1)
            if payload.get("delete") is True:
                credential_store.delete(ref)
                self._json_response(200, {"credential_ref": ref, "status": "DELETED", "secrets_returned": False})
            else:
                storage = credential_store.set(ref, payload["value"])
                self._json_response(200, {"credential_ref": ref, "status": "CONFIGURED", "storage": storage, "secrets_returned": False})
            return
        if path == "/api/v2/tool-calls":
            item = tool_broker.propose(thread_id=payload["thread_id"], turn_id=payload["turn_id"], tool_name=payload["tool_name"], arguments=payload.get("arguments", {}), permission_mode=payload["permission_mode"])
            self._json_response(201, item)
            return
        if path == "/api/v2/owner-direct/discover":
            self._json_response(200, tool_broker.owner_direct.discover(**payload))
            return
        if path == "/api/v2/owner-direct/writes/prepare":
            self._json_response(201, tool_broker.owner_direct.prepare_write(**payload))
            return
        match = re.fullmatch(r"/api/v2/owner-direct/writes/(odplan_[A-Za-z0-9_-]{16,64})/confirm", path)
        if match:
            self._json_response(200, tool_broker.owner_direct.confirm_write(match.group(1), owner_session_digest=owner_sessions.digest(owner_session)))
            return
        if path == "/api/v2/owner-direct/identity-audit":
            self._json_response(200, tool_broker.owner_direct.identity_audit(**payload))
            return
        match = re.fullmatch(r"/api/v2/tool-calls/(tcall_[A-Za-z0-9_-]{16,64})/invoke", path)
        if match:
            self._json_response(200, tool_broker.invoke(match.group(1), owner_session_digest=owner_sessions.digest(owner_session)))
            return
        match = re.fullmatch(r"/api/v2/live-reads/(lread_[A-Za-z0-9_-]{16,64})/approve", path)
        if match:
            item = tool_broker.approve_live_read(
                match.group(1),
                payload["approval_phrase"],
                owner_session_digest=owner_sessions.digest(owner_session),
            )
            self._json_response(200, item)
            return
        match = re.fullmatch(r"/api/v2/live-reads/(lread_[A-Za-z0-9_-]{16,64})/execute", path)
        if match:
            item = tool_broker.execute_live_read(
                match.group(1),
                payload["approval_id"],
                owner_session_digest=owner_sessions.digest(owner_session),
            )
            self._json_response(200, item)
            return
        match = re.fullmatch(r"/api/v2/workspace/plans/(wplan_[A-Za-z0-9_-]{16,64})/approve", path)
        if match:
            item = tool_broker.approve_patch(match.group(1), payload["approval_phrase"], owner_session_digest=owner_sessions.digest(owner_session))
            self._json_response(200, item)
            return
        match = re.fullmatch(r"/api/v2/workspace/plans/(wplan_[A-Za-z0-9_-]{16,64})/execute", path)
        if match:
            item = tool_broker.apply_approved_patch(match.group(1), payload["approval_id"], owner_session_digest=owner_sessions.digest(owner_session))
            self._json_response(200, item)
            return
        match = re.fullmatch(r"/api/v2/workspace/plans/(wplan_[A-Za-z0-9_-]{16,64})/rollback/prepare", path)
        if match:
            self._json_response(200, tool_broker.prepare_patch_rollback(match.group(1)))
            return
        match = re.fullmatch(r"/api/v2/workspace/rollbacks/(wrollback_[A-Za-z0-9_-]{16,64})/approve", path)
        if match:
            item = tool_broker.approve_patch_rollback(match.group(1), payload["approval_phrase"], owner_session_digest=owner_sessions.digest(owner_session))
            self._json_response(200, item)
            return
        match = re.fullmatch(r"/api/v2/workspace/rollbacks/(wrollback_[A-Za-z0-9_-]{16,64})/execute", path)
        if match:
            item = tool_broker.apply_approved_rollback(match.group(1), payload["approval_id"], owner_session_digest=owner_sessions.digest(owner_session))
            self._json_response(200, item)
            return
        match = re.fullmatch(r"/api/v2/p10/plans/(p10-(?:[a-f0-9]{20}|rb-[a-f0-9]{16}))/approve", path)
        if match:
            item = tool_broker.p10.approve(
                match.group(1), payload["approval_phrase"], owner_reference=OWNER_REFERENCE,
                source="local", owner_session_digest=owner_sessions.digest(owner_session),
            )
            self._json_response(200, item)
            return
        match = re.fullmatch(r"/api/v2/p10/plans/(p10-(?:[a-f0-9]{20}|rb-[a-f0-9]{16}))/execute", path)
        if match:
            item = tool_broker.p10.execute(match.group(1), owner_session_digest=owner_sessions.digest(owner_session))
            self._json_response(200, item)
            return
        match = re.fullmatch(r"/api/v2/p10/plans/(p10-(?:[a-f0-9]{20}|rb-[a-f0-9]{16}))/cancel", path)
        if match:
            self._json_response(200, tool_broker.p10.request_cancel(match.group(1)))
            return
        match = re.fullmatch(r"/api/v2/p10/plans/(p10-(?:[a-f0-9]{20}|rb-[a-f0-9]{16}))/rollback/prepare", path)
        if match:
            item = tool_broker.p10.prepare_rollback(match.group(1))
            self._json_response(200, item)
            return
        raise ValueError("P11 endpoint not found.")

    def _p10_client_host(self) -> str:
        return self.client_address[0] if self.client_address else ""

    def _p10_require_local(self) -> None:
        if not p10_api.is_local(self._p10_client_host()):
            raise P10SafetyError("P10 endpoints are available only from the local interface.")
        if not p10_api.is_same_origin_loopback(self.headers.get("Host"), self.headers.get("Origin")):
            raise P10SafetyError("P10 endpoints require a same-origin loopback host.")

    def _p10_authorize_mutation(self, body: Dict[str, Any]) -> None:
        p10_api.authorize_mutation(
            client_host=self._p10_client_host(),
            csrf_token=self.headers.get("X-P10-CSRF"),
            nonce=body.get("request_nonce"),
            host_header=self.headers.get("Host"),
            origin_header=self.headers.get("Origin"),
        )

    def _p10_response(self, callback, *, success_code: int = 200):
        try:
            payload = callback()
        except (P10SafetyError, ValueError, KeyError, jsonschema.ValidationError) as exc:
            self._set_headers(409)
            self.wfile.write(json.dumps({"status": "P10_REJECTED", "error": str(exc), "live_connection_attempted": False, "persistence_attempted": False}).encode("utf-8"))
            return
        self._set_headers(success_code)
        self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))

    def _handle_p10_session(self):
        self._p10_response(lambda: (self._p10_require_local(), p10_api.session_metadata())[1])

    def _handle_p10_operations(self):
        self._p10_response(lambda: (self._p10_require_local(), p10_api.engine.catalog.list_metadata())[1])

    def _handle_p10_readiness(self):
        self._p10_response(lambda: (self._p10_require_local(), p10_readiness.status())[1])

    def _handle_p10_plan_get(self, plan_id: str):
        self._p10_response(lambda: (self._p10_require_local(), p10_api.engine.get_plan(plan_id))[1])

    def _handle_p10_result_get(self, execution_id: str):
        self._p10_response(lambda: (self._p10_require_local(), p10_api.engine.get_result(execution_id))[1])

    def _handle_p10_prepare(self, body: Dict[str, Any]):
        def action():
            self._p10_authorize_mutation(body)
            session_digest = owner_sessions.digest(self._require_owner())
            allowed = {"operation_id", "binding_id", "target", "identity_pin", "parameters", "evidence", "owner_reference", "request_nonce"}
            if set(body).difference(allowed):
                raise P10SafetyError("Unknown P10 prepare request fields were rejected.")
            return p10_api.engine.prepare(
                body.get("operation_id", ""), binding_id=body.get("binding_id", ""), target=body.get("target", ""),
                identity_pin=body.get("identity_pin", ""), parameters=body.get("parameters"), evidence=body.get("evidence"),
                owner_reference=body.get("owner_reference", ""),
                owner_session_digest=session_digest,
            )
        self._p10_response(action, success_code=201)

    def _handle_p10_prepare_critical(self, body: Dict[str, Any]):
        def action():
            self._p10_authorize_mutation(body)
            session_digest = owner_sessions.digest(self._require_owner())
            allowed = {"platform", "protocol", "binding_id", "target", "identity_pin", "commands", "rollback_commands", "evidence", "warning", "irreversible", "owner_reference", "request_nonce"}
            if set(body).difference(allowed):
                raise P10SafetyError("Unknown critical prepare request fields were rejected.")
            return p10_api.engine.prepare_critical_exception(
                platform=body.get("platform", ""), protocol=body.get("protocol", ""), binding_id=body.get("binding_id", ""), target=body.get("target", ""),
                identity_pin=body.get("identity_pin", ""), commands=body.get("commands"), rollback_commands=body.get("rollback_commands", []),
                evidence=body.get("evidence"), warning=body.get("warning"), irreversible=body.get("irreversible") is True,
                owner_reference=body.get("owner_reference", ""),
                owner_session_digest=session_digest,
            )
        self._p10_response(action, success_code=201)

    def _handle_p10_approve(self, plan_id: str, body: Dict[str, Any]):
        def action():
            self._p10_authorize_mutation(body)
            session_digest = owner_sessions.digest(self._require_owner())
            if set(body) != {"approval_phrase", "owner_reference", "request_nonce"}:
                raise P10SafetyError("Approval request fields do not match the exact contract.")
            p10_api.engine._validate_contract("p10-approval-request.schema.json", {
                "plan_id": plan_id, "owner_reference": body["owner_reference"],
                "approval_phrase": body["approval_phrase"], "csrf_token": self.headers.get("X-P10-CSRF"),
                "request_nonce": body["request_nonce"],
            })
            return p10_api.engine.approve(
                plan_id, body["approval_phrase"], owner_reference=body["owner_reference"],
                source="local", owner_session_digest=session_digest,
            )
        self._p10_response(action)

    def _handle_p10_execute(self, plan_id: str, body: Dict[str, Any]):
        def action():
            self._p10_authorize_mutation(body)
            session_digest = owner_sessions.digest(self._require_owner())
            if set(body) != {"request_nonce"}:
                raise P10SafetyError("Execute request fields do not match the exact contract.")
            return p10_api.engine.execute(plan_id, owner_session_digest=session_digest)
        self._p10_response(action)

    def _handle_p10_rollback_prepare(self, plan_id: str, body: Dict[str, Any]):
        def action():
            self._p10_authorize_mutation(body)
            if set(body) != {"request_nonce"}:
                raise P10SafetyError("Rollback prepare request fields do not match the exact contract.")
            return p10_api.engine.prepare_rollback(plan_id)
        self._p10_response(action, success_code=201)

    def _handle_p8_status(self):
        try:
            payload = P8TroubleshootingEngine(base_dir=base_dir).status()
        except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError, jsonschema.ValidationError) as exc:
            self._set_headers(500)
            self.wfile.write(json.dumps({"status": "P8_CONFIGURATION_ERROR", "error": str(exc), "live_connection_attempted": False}).encode("utf-8"))
            return
        self._set_headers(200)
        self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))

    def _handle_p9_status(self):
        try:
            payload = P9DiagnosticEngine(base_dir=base_dir).status()
        except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError, jsonschema.ValidationError) as exc:
            self._set_headers(500)
            self.wfile.write(json.dumps({"status": "P9_CONFIGURATION_ERROR", "error": str(exc), "live_connection_attempted": False}).encode("utf-8"))
            return
        self._set_headers(200)
        self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))

    def _handle_p8_plan(self, body: Dict[str, Any]):
        try:
            # The HTTP surface is planning-only. Live evidence must enter through
            # an owner-gated local session, never as untrusted browser content.
            request = {key: body.get(key) for key in ("scenario_id", "binding_id", "symptom")}
            payload = P8TroubleshootingEngine(base_dir=base_dir).plan(request)
        except ValueError as exc:
            self._set_headers(400)
            self.wfile.write(json.dumps({"status": "P8_PLAN_REJECTED", "error": str(exc), "live_connection_attempted": False, "persistence_attempted": False, "remediation_attempted": False}).encode("utf-8"))
            return
        self._set_headers(200)
        self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))

    def _handle_p9_plan(self, body: Dict[str, Any]):
        try:
            request = {key: body.get(key) for key in ("scenario_id", "binding_id", "symptom")}
            payload = P9DiagnosticEngine(base_dir=base_dir).plan(request)
        except ValueError as exc:
            self._set_headers(400)
            self.wfile.write(json.dumps({"status": "P9_PLAN_REJECTED", "error": str(exc), "live_connection_attempted": False, "persistence_attempted": False, "remediation_attempted": False}).encode("utf-8"))
            return
        self._set_headers(200)
        self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))

    def _handle_incident_workflow_status(self, params: Dict[str, Any]):
        try:
            status = IncidentWorkflowGovernance(base_dir=base_dir).evaluate()
        except ValueError as exc:
            self._set_headers(400)
            self.wfile.write(
                json.dumps(
                    {
                        "status": "P4_WORKFLOW_GOVERNANCE_REJECTED",
                        "error": str(exc),
                        "persistence_attempted": False,
                        "assignment_attempted": False,
                        "notification_sent": False,
                    }
                ).encode("utf-8")
            )
            return
        self._set_headers(200)
        self.wfile.write(json.dumps(status, indent=2).encode("utf-8"))

    def _handle_incident_intake(self, body: Dict[str, Any]):
        try:
            intake = IncidentIntakeService(base_dir=base_dir).create_intake(body)
        except ValueError as exc:
            self._set_headers(400)
            self.wfile.write(
                json.dumps(
                    {
                        "status": "P4_INTAKE_REJECTED",
                        "error": str(exc),
                        "live_connection_attempted": False,
                        "notification_sent": False,
                        "persistence_attempted": False,
                        "remediation_attempted": False,
                    }
                ).encode("utf-8")
            )
            return
        self._set_headers(200)
        self.wfile.write(json.dumps(intake, indent=2).encode("utf-8"))

    def _handle_dashboard(self):
        builder = EntityIndexBuilder(base_dir=base_dir)
        idx_data = builder.build_index()
        entities = idx_data.get("entities", [])
        status_counts: Dict[str, int] = {}
        for entity in entities:
            knowledge_status = str(entity.get("knowledge_status", "unknown"))
            status_counts[knowledge_status] = status_counts.get(knowledge_status, 0) + 1

        driver_statuses = {
            protocol: "PLANNING_ONLY_NOT_CONFIGURED"
            for protocol in ["ssh", "rest", "powershell", "winrm", "vmware", "sql", "snmp"]
        }
        runbook_registry = RunbookRegistry(base_dir=base_dir)
        runbook_index = runbook_registry.build_registry()
        runbook_coverage = runbook_registry.coverage_report(entities)
        connector_registry = ConnectorRegistry(base_dir=base_dir)
        connector_catalog = connector_registry.public_catalog()
        connector_coverage = connector_registry.coverage_report()
        transport_status = TransportRegistry(base_dir=base_dir).public_status()

        res = {
            "system": "MNE_Brain Release 2",
            "version": "2.0.0",
            "status": "DEVELOPMENT_ONLY",
            "operational_ready": False,
            "environment": "OFFLINE_DEVELOPMENT",
            "gui_rule": "Presentation ONLY — ZERO Business Logic in GUI",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "llm_provider": "local_deterministic",
            "total_entities": idx_data.get("total_entities", 0),
            "knowledge_status_counts": status_counts,
            "driver_statuses": driver_statuses,
            "verification_queue_pending": 0,
            "live_verification": "NOT_CONFIGURED",
            "alert_ingestion": "DISABLED_BY_POLICY",
            "active_alerts": [],
            "runbooks": runbook_index.get("total_runbooks", 0),
            "operational_runbook_coverage_percent": runbook_coverage[
                "operational_coverage_percent"
            ],
            "operational_runbook_readiness": runbook_coverage[
                "operational_runbook_readiness"
            ],
            "connector_families": connector_catalog["total_connectors"],
            "offline_connector_coverage_percent": connector_coverage[
                "offline_validation_coverage_percent"
            ],
            "offline_connector_readiness": connector_coverage[
                "full_offline_connector_readiness"
            ],
            "live_transport_coverage_percent": connector_coverage[
                "live_transport_coverage_percent"
            ],
            "p7_transport_implementation_coverage_percent": transport_status[
                "transport_implementation_coverage_percent"
            ],
            "p7_transport_driver_count": len(transport_status["drivers"]),
            "p7_identity_conflicts": transport_status["identity_conflicts"],
            "p7_live_enabled": transport_status["live_enabled"],
            "p7_active_bindings": transport_status["credential_bindings"]["active_bindings"],
            "p7_owner_excluded_bindings": transport_status["credential_bindings"]["owner_excluded_bindings"],
        }
        self._set_headers(200)
        self.wfile.write(json.dumps(res, indent=2).encode("utf-8"))

    def _handle_runbooks(self, params):
        registry = RunbookRegistry(base_dir=base_dir)
        entities = EntityIndexBuilder(base_dir=base_dir).build_index(persist=False)["entities"]
        index = registry.build_registry()
        response = {
            "mode": registry.MODE,
            "owner_reference": registry.OWNER_REFERENCE,
            "total_runbooks": index["total_runbooks"],
            "coverage": registry.coverage_report(entities),
            "runbooks": index["runbooks"],
            "body_included": False,
            "live_connection_attempted": False,
            "notification_sent": False,
            "persistence_attempted": False,
            "remediation_attempted": False,
        }
        self._set_headers(200)
        self.wfile.write(json.dumps(response, indent=2).encode("utf-8"))

    def _handle_connectors(self, params):
        registry = ConnectorRegistry(base_dir=base_dir)
        response = registry.public_catalog()
        response["coverage"] = registry.coverage_report()
        response.update(
            {
                "live_collection_enabled": False,
                "body_included": False,
                "live_connection_attempted": False,
                "notification_sent": False,
                "persistence_attempted": False,
                "remediation_attempted": False,
            }
        )
        self._set_headers(200)
        self.wfile.write(json.dumps(response, indent=2).encode("utf-8"))

    def _handle_transports(self, params):
        """Expose configuration/readiness only; never start a live connection."""
        response = TransportRegistry(base_dir=base_dir).public_status()
        response.update({
            "live_connection_attempted": False,
            "authenticated_validation_results_persisted": False,
            "raw_output_included": False,
            "credentials_included": False,
        })
        self._set_headers(200)
        self.wfile.write(json.dumps(response, indent=2).encode("utf-8"))

    def _handle_devices(self, params):
        builder = EntityIndexBuilder(base_dir=base_dir)
        idx_data = builder.build_index()
        entities = idx_data.get("entities", [])
        
        target_id = params.get("id", [None])[0]
        if target_id:
            matched = [e for e in entities if e["entity_id"] == target_id]
            res = matched[0] if matched else {"error": "Device not found"}
        else:
            res = {"total": len(entities), "devices": entities}

        self._set_headers(200)
        self.wfile.write(json.dumps(res, indent=2).encode("utf-8"))

    def _handle_knowledge(self, params):
        knowledge_dir = base_dir / "knowledge"
        notes = []
        if knowledge_dir.exists():
            for md_file in sorted(knowledge_dir.rglob("*.md")):
                try:
                    rel_path = md_file.relative_to(base_dir).as_posix()
                    category = md_file.parent.name
                    with open(md_file, 'r', encoding='utf-8') as f:
                        raw_text = f.read()

                    meta = {}
                    body = raw_text
                    if raw_text.startswith("---"):
                        parts = raw_text.split("---", 2)
                        if len(parts) >= 3:
                            meta = yaml.safe_load(parts[1]) or {}
                            body = parts[2].strip()

                    notes.append({
                        "file_name": md_file.name,
                        "relative_path": rel_path,
                        "category": category,
                        "title": meta.get("name") or meta.get("id") or md_file.stem,
                        "entity_id": meta.get("id", ""),
                        "frontmatter": meta,
                        "content": raw_text,
                        "body": body
                    })
                except Exception:
                    pass

        queue_file = base_dir / "operations" / "discovery" / "review_queue.json"
        review_queue = []
        if queue_file.exists():
            try:
                with open(queue_file, 'r', encoding='utf-8') as qf:
                    review_queue = json.load(qf)
            except Exception:
                review_queue = []

        target_file = params.get("file", [None])[0]
        selected_note = None
        if target_file:
            matched = [n for n in notes if n["relative_path"] == target_file or n["file_name"] == target_file]
            if matched:
                selected_note = matched[0]

        res = {
            "total_notes": len(notes),
            "notes": notes,
            "review_queue": review_queue,
            "selected_note": selected_note
        }
        self._set_headers(200)
        self.wfile.write(json.dumps(res, indent=2).encode("utf-8"))

    def _handle_investigations(self, params):
        obs_file = base_dir / "operations" / "logs" / "observability.jsonl"
        traces = []
        if obs_file.exists():
            try:
                with open(obs_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            traces.append(json.loads(line.strip()))
            except Exception:
                pass

        self._set_headers(200)
        self.wfile.write(json.dumps({"total_traces": len(traces), "traces": traces[-50:]}, indent=2).encode("utf-8"))

    def _handle_actions(self, params):
        actions_dir = base_dir / "actions" / "approved"
        actions = []
        if actions_dir.exists():
            for act_file in sorted(actions_dir.glob("*.yaml")):
                try:
                    with open(act_file, 'r', encoding='utf-8') as af:
                        action = yaml.safe_load(af)
                    if not isinstance(action, dict):
                        continue
                    command = str(action.get("command", ""))
                    rollback_command = str(action.get("rollback_command", ""))
                    actions.append({
                        "action_id": action.get("action_id", act_file.stem),
                        "title": action.get("title", "Untitled action"),
                        "template_status": action.get("template_status", "unreviewed"),
                        "risk_level": action.get("risk_level"),
                        "platform": action.get("platform"),
                        "pre_check_count": len(action.get("pre_checks", [])),
                        "post_check_count": len(action.get("post_checks", [])),
                        "command_fingerprint": hashlib.sha256(command.encode("utf-8")).hexdigest(),
                        "rollback_fingerprint": hashlib.sha256(
                            rollback_command.encode("utf-8")
                        ).hexdigest(),
                        "execution_permitted": False,
                    })
                except Exception:
                    pass

        self._set_headers(200)
        self.wfile.write(json.dumps({"total_actions": len(actions), "actions": actions}, indent=2).encode("utf-8"))

    def _handle_automation(self):
        listener = WebhookAlertListener(base_dir=base_dir)
        res = {
            "n8n_status": "NOT_CONFIGURED",
            "webhook_listener": (
                "ENABLED_AWAITING_AUTHENTICATED_GATEWAY"
                if listener.ingestion_enabled
                else "DISABLED_BY_POLICY"
            ),
            "automatic_investigation": False,
            "automatic_remediation": False,
            "recent_executions": [],
        }
        self._set_headers(200)
        self.wfile.write(json.dumps(res, indent=2).encode("utf-8"))

    def _handle_logs(self, params):
        audit_file = base_dir / "operations" / "actions" / "audit_log.jsonl"
        audit_logs = []
        if audit_file.exists():
            try:
                with open(audit_file, 'r', encoding='utf-8') as af:
                    for line in af:
                        if line.strip():
                            audit_logs.append(json.loads(line))
            except Exception:
                audit_logs = []

        self._set_headers(200)
        self.wfile.write(json.dumps({"audit_logs": audit_logs[-50:]}, indent=2).encode("utf-8"))

    def _handle_settings_get(self):
        refs = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LOCAL_OPENAI_COMPATIBLE_KEY"]
        res = {
            "llm_provider": os.getenv("LLM_PROVIDER", "prv_local_deterministic"),
            "evidence_token_limit": 1500,
            "policy_enforcement": "STRICT",
            "zero_auto_overwrite": True,
            "credentials_status": {ref: credential_store.status(ref)["status"] for ref in refs},
            "credential_storage": "KEYRING_PREFERRED_ENV_FALLBACK",
            "secrets_returned": False,
        }
        self._json_response(200, res)

    def _handle_settings_post(self, body: Dict[str, Any]):
        provider = body.get("llm_provider", "prv_local_deterministic")
        provider_registry.get(provider)
        os.environ["LLM_PROVIDER"] = provider
        self._json_response(200, {"status": "UPDATED", "llm_provider": provider, "secrets_returned": False})

    def _handle_settings_auto(self):
        provider = "prv_local_deterministic"
        os.environ["LLM_PROVIDER"] = provider
        self._json_response(200, {"status": "SUCCESS", "llm_provider": provider, "message": "Selected deterministic local fallback; external providers require explicit enablement and data authorization."})

    def _handle_oauth_url(self):
        self._json_response(410, {"status": "QUARANTINED"})

    def _handle_oauth_status(self):
        self._json_response(410, {"status": "QUARANTINED", "secrets_returned": False})

    def _handle_oauth_token(self, body: Dict[str, Any]):
        self._json_response(410, {"status": "QUARANTINED"})

    def _handle_oauth_callback(self, params: Dict[str, Any]):
        self._json_response(410, {"status": "QUARANTINED"})

    def _handle_search(self, params):
        q = params.get("q", [""])[0].lower()
        builder = EntityIndexBuilder(base_dir=base_dir)
        idx_data = builder.build_index()
        
        matched_devices = [e for e in idx_data.get("entities", []) if q in e["name"].lower() or q in e["entity_id"].lower() or q in e["ip"].lower()]
        
        res = {
            "query": q,
            "matched_devices": matched_devices
        }
        self._set_headers(200)
        self.wfile.write(json.dumps(res, indent=2).encode("utf-8"))

    def _handle_chat(self, body: Dict[str, Any]):
        question = body.get("question", "")
        if not question:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": "Missing question field"}).encode("utf-8"))
            return

        tracer = ObservabilityTracer(base_dir=base_dir, persist=False)
        try:
            incident_case = IncidentCaseManager(base_dir=base_dir).build_case(
                question,
                impact_context=body.get("impact_context"),
                prior_case=body.get("prior_case"),
                check_updates=body.get("check_updates"),
            )
        except ValueError as exc:
            self._set_headers(400)
            self.wfile.write(
                json.dumps(
                    {
                        "status": "P4_INPUT_REJECTED",
                        "error": str(exc),
                        "live_connection_attempted": False,
                        "persistence_attempted": False,
                        "remediation_attempted": False,
                    }
                ).encode("utf-8")
            )
            return
        investigation = incident_case["investigation"]
        tracer.trace_step(
            "incident_case_manager",
            "build_case",
            status=incident_case["case_state"],
            details={
                "case_id": incident_case["case_id"],
                "provisional_priority": incident_case["priority"]["classification"],
                "target_entity_id": (investigation.get("target") or {}).get("entity_id"),
                "metrics": incident_case["metrics"],
                "safety": incident_case["safety"],
            },
        )

        route_res = investigation["route"]
        evidence = investigation["evidence_pack"]
        reason_eval = investigation["reasoning"]
        policy_res = investigation["policy"]
        entities = [investigation["target"]] if investigation.get("target") else []
        verify_res = {
            "status": "NOT_RUN",
            "profile_name": None,
            "trust_level": 0,
            "checks_executed": 0,
            "connection_attempted": False,
            "reason": "P3 produces offline evidence objectives; P2 live activation remains separately gated.",
        }
        drift_res = {
            "status": "NOT_RUN",
            "persistence": "NOT_REQUESTED",
            "reason": "Knowledge drift requires accepted live evidence and is not inferred from an offline question.",
        }

        provider_name = os.getenv("LLM_PROVIDER", "local_fallback")
        llm = LLMAdapter(provider=provider_name, base_dir=base_dir)
        final_res = llm.generate_response(question, evidence)

        res_payload = {
            "correlation_id": tracer.correlation_id,
            "investigation_id": tracer.investigation_id,
            "p3_investigation_id": investigation["investigation_id"],
            "p4_case_id": incident_case["case_id"],
            "question": question,
            "investigation_status": investigation["status"],
            "case_state": incident_case["case_state"],
            "provisional_priority": incident_case["priority"],
            "reported_impact": incident_case["impact"],
            "ownership": incident_case["ownership"],
            "incident_case": {
                key: value for key, value in incident_case.items() if key != "investigation"
            },
            "route": route_res,
            "entities": entities,
            "evidence_pack": evidence,
            "reasoning": reason_eval,
            "policy": policy_res,
            "live_verification": verify_res,
            "knowledge_lifecycle": drift_res,
            "dependency_context": investigation["dependency_context"],
            "next_checks": investigation["next_checks"],
            "ai_handoff": investigation["ai_handoff"],
            "metrics": investigation["metrics"],
            "safety": investigation["safety"],
            "trace": tracer.get_summary(),
            "response": final_res,
            "clarification_request": route_res.get("clarification_request")
        }
        self._set_headers(200)
        self.wfile.write(json.dumps(res_payload, indent=2).encode("utf-8"))

    def _handle_action_execute(self, body: Dict[str, Any]):
        action_id = body.get("action_id", "")
        rem_engine = RemediationEngine(base_dir=base_dir)

        try:
            rem_res = rem_engine.execute_remediation(
                action_id,
                owner_reference=body.get("owner_reference"),
                explicit_owner_instruction=body.get("explicit_owner_instruction") is True,
            )
            response_code = 202 if rem_res.get("status") == "NOT_EXECUTED" else 409
            self._set_headers(response_code)
            self.wfile.write(json.dumps(rem_res, indent=2).encode("utf-8"))
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({"status": "FAILED", "error": str(e)}).encode("utf-8"))

    def _handle_knowledge_promote(self, body: Dict[str, Any]):
        proposal_id = body.get("proposal_id", "")
        lifecycle = KnowledgeLifecycleEngine(base_dir=base_dir)
        res = lifecycle.promote_to_canonical(
            proposal_id,
            explicit_owner_instruction=body.get("explicit_owner_instruction") is True,
        )
        self._set_headers(200)
        self.wfile.write(json.dumps(res, indent=2).encode("utf-8"))

    def _handle_automation_trigger(self, body: Dict[str, Any]):
        listener = WebhookAlertListener(base_dir=base_dir)
        res = listener.process_alert_payload(body)
        response_code = {
            "INGESTION_DISABLED": 503,
            "UNAUTHENTICATED": 401,
            "ACCEPTED_FOR_POLICY_REVIEW": 202,
        }.get(res.get("status"), 400)
        self._set_headers(response_code)
        self.wfile.write(json.dumps(res, indent=2).encode("utf-8"))

def run_api_server(port: int | None = None, host: str | None = None):
    bind_host = host or str(security_policy.get("bind_host", "127.0.0.1"))
    if not owner_sessions.is_loopback(bind_host):
        raise ValueError("The P11 GUI server binds to loopback only by default and rejects non-loopback hosts.")
    configured = os.getenv("MNE_BRAIN_PORT", str(security_policy.get("bind_port", 8080)))
    try:
        selected_port = int(configured) if port is None else int(port)
    except (TypeError, ValueError) as exc:
        raise ValueError("MNE_BRAIN_PORT must be a valid TCP port number.") from exc
    if not 0 <= selected_port <= 65535:
        raise ValueError("The configured GUI port is outside the valid TCP port range.")
    try:
        bound_server = BoundedThreadingHTTPServer(
            (bind_host, selected_port), MNEBrainAPIHandler,
            max_workers=int(security_policy.get("http", {}).get("max_workers", 16)),
        )
    except OSError as exc:
        raise OSError(f"GUI port {selected_port} on {bind_host} is unavailable; stop the conflicting process or configure MNE_BRAIN_PORT.") from exc
    readiness = _codex_readiness(start_process=True)
    opencode_readiness = _opencode_readiness(start_process=True)
    antigravity_readiness = _antigravity_readiness(start_process=True)
    print(f"MNE_Brain P11 REST API Server running on http://{bind_host}:{selected_port} (bounded concurrent mode)...")
    print(f"Codex App Server readiness: {readiness['status']} (ChatGPT session, service tier {readiness['service_tier']}).")
    print(f"OpenCode readiness: {opencode_readiness['status']} (protected loopback HTTP/SSE server).")
    print(f"Antigravity CLI readiness: {antigravity_readiness['status']} (version {antigravity_readiness.get('version')}, default model {antigravity_readiness.get('default_model')}).")
    try:
        bound_server.serve_forever()
    finally:
        conversation_engine.codex.stop(cleanup_workspaces=True)
        conversation_engine.opencode.stop()
        bound_server.server_close()

if __name__ == "__main__":
    run_api_server()
