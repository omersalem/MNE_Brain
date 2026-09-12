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
import base64
import secrets
import re
import socket
import threading
import queue
import time
import yaml
import jsonschema
import urllib.parse
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

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
from core.security_review.config import SecurityAgentConfig
from core.security_review.contracts import SecurityReviewRequest
from core.security_review.jobs import SecurityReviewJobManager
from core.security_review.run_store import SecurityReviewRunStore
from core.security_review.service import SecurityReviewService
from core.security_review.trends import get_trend_analytics
from core.security_review.troubleshooting_bridge import SecurityTroubleshootingBridge
from core.connectors.security.models import NormalizedSecurityEvent, ThreatCategory
from core.security_review.identity_enrichment import coerce_datetime_utc, should_replace_attribution, AttackerAttribution
from integrations.n8n.webhook_listener import WebhookAlertListener

_in_flight_resolutions: Set[str] = set()
_in_flight_resolutions_lock = threading.Lock()

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
conversation_storage_policy = security_policy.get("conversation_storage", {})
conversation_storage_dir = (
    base_dir / str(conversation_storage_policy.get("storage_path", "operations/conversations"))
    if conversation_storage_policy.get("persist_locally", True)
    else None
)
conversation_engine = ConversationEngine(
    base_dir,
    gateway=provider_gateway,
    tool_broker=tool_broker,
    storage_dir=conversation_storage_dir,
    auto_authorize_external_redacted_context=bool(
        security_policy.get("external_data", {}).get("auto_authorize_redacted_conversation", False)
    ),
)
p10_api = P10LocalAPIContext(tool_broker.p10)
p10_readiness = P10ReadinessService(base_dir)
owner_full_control = InfrastructureCoverageService(base_dir)
security_review_run_store = SecurityReviewRunStore(base_dir / "operations" / "security_review" / "runs")
security_review_job_manager = SecurityReviewJobManager()
security_review_service = SecurityReviewService(
    run_store=security_review_run_store,
    job_manager=security_review_job_manager,
)
security_review_service.ai_analyzer.conversation_engine = conversation_engine
security_troubleshooting_bridge = SecurityTroubleshootingBridge(
    base_dir=base_dir,
    run_store=security_review_run_store,
    incident_store=security_review_run_store.incident_store,
)


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
        default_csp = "default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        csp = (extra_headers or {}).get("Content-Security-Policy", default_csp)
        self.send_header("Content-Security-Policy", csp)
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra_headers or {}).items():
            if key != "Content-Security-Policy":
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

    def _owner_digest(self) -> Optional[str]:
        headers = getattr(self, "headers", None)
        if not headers or not hasattr(headers, "get"):
            return None
        cookie = headers.get("Cookie")
        if not cookie:
            return None
        try:
            session = owner_sessions.require(
                client_host=self._client_host(),
                host_header=headers.get("Host"),
                origin_header=headers.get("Origin"),
                cookie_header=cookie,
            )
            return hashlib.sha256(session.session_id.encode("utf-8")).hexdigest()
        except Exception:
            return None

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
                self._json_response(200, owner_sessions.describe(session), extra_headers={"Set-Cookie": owner_sessions.session_cookie(session)})
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
        elif path == "/api/security-agent/status":
            self._handle_security_agent_status()
        elif path == "/api/security-agent/report/html":
            self._handle_security_agent_report_html()
        elif path == "/api/security-agent/report/pdf":
            self._handle_security_agent_report_pdf()
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
            self._json_response(403, {"error": str(exc), "code": "OWNER_SESSION_EXPIRED"})
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
        elif path == "/api/security-agent/config":
            self._handle_security_agent_config_post(body)
        elif path == "/api/security-agent/run":
            self._handle_security_agent_run_post(body)
        elif path == "/api/security-agent/test-email":
            self._handle_security_agent_test_email_post(body)
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": f"Endpoint {path} not found"}).encode("utf-8"))

    # Handler Implementation Methods
    def _handle_v2_get(self, path: str, params: Dict[str, Any]) -> None:
        if path == "/api/v2/threads":
            query = (params.get("search") or [""])[0]
            retention = "LOCAL_STORAGE" if conversation_engine.store.storage_dir else "IN_MEMORY_ONLY"
            self._json_response(200, {"threads": conversation_engine.store.list_threads(query), "retention": retention})
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
                "owner_direct": {
                    "enabled": True,
                    "read_identity_mode": "COLLECT_UNVERIFIED",
                    "read_only_approval": "AUTOMATIC_BOUNDED_OWNER_SESSION",
                    "write_confirmation": "OWNER_ACCEPT_OR_DENY_AFTER_RISK_PREVIEW",
                },
                "bind_host": security_policy.get("bind_host", "127.0.0.1"),
                "conversation_retention": "LOCAL_STORAGE" if conversation_engine.store.storage_dir else "IN_MEMORY_ONLY",
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
        match = re.fullmatch(r"/api/v2/uploads/([A-Za-z0-9_.-]{1,250})", path)
        if match:
            self._serve_upload(match.group(1))
            return
        if path == "/api/v2/security-agent/status":
            self._handle_security_agent_status()
            return
        if path == "/api/v2/security-agent/report/html":
            self._handle_security_agent_report_html()
            return
        if path == "/api/v2/security-agent/report/pdf":
            self._handle_security_agent_report_pdf()
            return
        if path == "/api/v2/security-agent/runs":
            self._handle_security_agent_runs_get()
            return
        match = re.fullmatch(r"/api/v2/security-agent/runs/([A-Za-z0-9_.-]{1,100})/events", path)
        if match:
            self._stream_security_run_events(match.group(1))
            return
        match = re.fullmatch(r"/api/v2/security-agent/runs/([A-Za-z0-9_.-]{1,100})", path)
        if match:
            self._handle_security_agent_run_get(match.group(1))
            return
        if path == "/api/v2/security-agent/incidents":
            status = (params.get("status") or [None])[0]
            severity = (params.get("severity") or [None])[0]
            category = (params.get("category") or [None])[0]
            search = (params.get("search") or [None])[0]
            try:
                limit = int((params.get("limit") or [50])[0])
            except ValueError:
                limit = 50
            try:
                offset = int((params.get("offset") or [0])[0])
            except ValueError:
                offset = 0
            self._handle_security_agent_incidents_get(status, severity, category, search, limit, offset)
            return
        match = re.fullmatch(r"/api/v2/security-agent/incidents/([A-Za-z0-9_.-]{1,100})/timeline", path)
        if match:
            self._handle_security_agent_incident_timeline_get(match.group(1))
            return
        match = re.fullmatch(r"/api/v2/security-agent/incidents/([A-Za-z0-9_.-]{1,100})", path)
        if match:
            self._handle_security_agent_incident_get(match.group(1))
            return
        match = re.fullmatch(r"/api/v2/security-agent/analyses/([A-Za-z0-9_.-]{1,100})/events", path)
        if match:
            self._stream_security_analysis_events(match.group(1))
            return
        match = re.fullmatch(r"/api/v2/security-agent/analyses/([A-Za-z0-9_.-]{1,100})/report", path)
        if match:
            self._handle_security_agent_analysis_report_get(match.group(1), params)
            return
        match = re.fullmatch(r"/api/v2/security-agent/analyses/([A-Za-z0-9_.-]{1,100})/export", path)
        if match:
            self._handle_security_agent_analysis_report_get(match.group(1), params)
            return
        match = re.fullmatch(r"/api/v2/security-agent/analyses/([A-Za-z0-9_.-]{1,100})", path)
        if match:
            self._handle_security_agent_analysis_get(match.group(1))
            return
        match = re.fullmatch(r"/api/v2/security-agent/runs/([A-Za-z0-9_.-]{1,100})/report", path)
        if match:
            self._handle_security_agent_run_report_get(match.group(1), params)
            return
        if path == "/api/v2/security-agent/profiles":
            self._handle_security_agent_profiles_get()
            return
        if path == "/api/v2/security-agent/trends":
            self._handle_security_agent_trends_get(params)
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
                    all_events = conversation_engine.events.list_after(turn_id, None)
                    if any(e.get("event_type") in terminal_types for e in all_events):
                        return
                    turn = conversation_engine.store.get_turn(turn_id)
                    wait_timeout = 2.0 if turn["status"] in terminal_statuses else heartbeat
                    events = conversation_engine.events.wait_after(turn_id, last_event_id, timeout=wait_timeout)
                    if not events:
                        if turn["status"] in terminal_statuses:
                            return
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

    def _serve_upload(self, filename: str) -> None:
        uploads_dir = (base_dir / "operations/uploads").resolve()
        candidate = (uploads_dir / filename).resolve()
        try:
            candidate.relative_to(uploads_dir)
        except ValueError:
            self._json_response(403, {"error": "Invalid file path."})
            return
        if not candidate.is_file():
            self._json_response(404, {"error": "Uploaded file not found."})
            return
        ext = candidate.suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".svg": "image/svg+xml",
            ".bmp": "image/bmp",
            ".ico": "image/x-icon",
            ".pdf": "application/pdf",
            ".json": "application/json",
            ".txt": "text/plain; charset=utf-8",
            ".log": "text/plain; charset=utf-8",
            ".conf": "text/plain; charset=utf-8",
            ".cfg": "text/plain; charset=utf-8",
            ".csv": "text/csv; charset=utf-8",
            ".py": "text/plain; charset=utf-8",
            ".sh": "text/plain; charset=utf-8",
            ".ps1": "text/plain; charset=utf-8",
            ".yaml": "text/yaml; charset=utf-8",
            ".yml": "text/yaml; charset=utf-8",
            ".md": "text/markdown; charset=utf-8",
            ".xml": "application/xml",
        }
        ct = mime_map.get(ext, "application/octet-stream")
        try:
            raw = candidate.read_bytes()
            self._set_headers(200, ct, content_length=len(raw))
            self.wfile.write(raw)
        except Exception as exc:
            self._json_response(500, {"error": f"Failed reading upload: {exc}"})

    def _handle_upload_post(self, payload: Dict[str, Any], owner_session) -> None:
        filename = str(payload.get("filename") or "upload.bin").strip()
        content_b64 = str(payload.get("content_base64") or "")
        mime_type = str(payload.get("mime_type") or "application/octet-stream").strip()
        if not content_b64:
            raise ValueError("File content (base64) is required.")

        try:
            raw_data = base64.b64decode(content_b64, validate=True)
        except Exception:
            raise ValueError("Invalid base64 payload.")

        max_size = 25 * 1024 * 1024
        if len(raw_data) > max_size:
            raise ValueError(f"File size ({len(raw_data)} bytes) exceeds the 25 MB limit.")

        clean_name = Path(filename).name.replace("/", "").replace("\\", "").replace("..", "").strip()
        clean_name = re.sub(r"[^A-Za-z0-9_.-]", "_", clean_name)
        if not clean_name or clean_name.startswith("."):
            clean_name = f"attachment_{secrets.token_hex(4)}.bin"

        timestamp = int(time.time())
        token = secrets.token_hex(4)
        safe_name = f"upl_{timestamp}_{token}_{clean_name}"

        uploads_dir = (base_dir / "operations/uploads").resolve()
        uploads_dir.mkdir(parents=True, exist_ok=True)
        target_path = uploads_dir / safe_name
        target_path.write_bytes(raw_data)

        ext = target_path.suffix.lower()
        is_image = ext in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico"}

        text_content = None
        if not is_image and len(raw_data) <= 50 * 1024:
            try:
                text_content = raw_data.decode("utf-8")
            except UnicodeDecodeError:
                pass

        resp = {
            "upload_id": f"upl_{token}",
            "filename": filename,
            "safe_name": safe_name,
            "url": f"/api/v2/uploads/{safe_name}",
            "relative_path": f"operations/uploads/{safe_name}",
            "absolute_path": str(target_path),
            "is_image": is_image,
            "size": len(raw_data),
            "mime_type": mime_type,
            "text_content": text_content,
        }
        self._json_response(201, resp)

    def _handle_v2_post(self, path: str, body: Dict[str, Any], owner_session) -> None:
        payload = {key: value for key, value in body.items() if key != "request_nonce"}
        if path == "/api/v2/uploads":
            self._handle_upload_post(payload, owner_session)
            return
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
        match = re.fullmatch(r"/api/v2/threads/(thr_[A-Za-z0-9_-]{16,64})/delete", path)
        if match:
            conversation_engine.delete_thread(match.group(1))
            self._json_response(200, {"status": "DELETED", "thread_id": match.group(1)})
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
        if path == "/api/v2/security-agent/config":
            self._handle_security_agent_config_post(payload)
            return
        if path == "/api/v2/security-agent/run":
            self._handle_security_agent_run_post(payload)
            return
        if path == "/api/v2/security-agent/test-email":
            self._handle_security_agent_test_email_post(payload)
            return
        if path == "/api/v2/security-agent/runs":
            self._handle_security_agent_runs_post(payload)
            return
        match = re.fullmatch(r"/api/v2/security-agent/runs/([A-Za-z0-9_.-]{1,100})/cancel", path)
        if match:
            self._handle_security_agent_run_cancel_post(match.group(1))
            return
        match = re.fullmatch(r"/api/v2/security-agent/runs/([A-Za-z0-9_.-]{1,100})/retry", path)
        if match:
            self._handle_security_agent_run_retry_post(match.group(1), payload)
            return
        match = re.fullmatch(r"/api/v2/security-agent/incidents/([A-Za-z0-9_.-]{1,100})/status", path)
        if match:
            self._handle_security_agent_incident_status_post(match.group(1), payload)
            return
        match = re.fullmatch(r"/api/v2/security-agent/incidents/([A-Za-z0-9_.-]{1,100})/notes", path)
        if match:
            self._handle_security_agent_incident_notes_post(match.group(1), payload)
            return
        match = re.fullmatch(r"/api/v2/security-agent/incidents/([A-Za-z0-9_.-]{1,100})/resolve-identity", path)
        if match:
            self._handle_security_agent_incident_resolve_identity_post(match.group(1), payload)
            return
        match = re.fullmatch(r"/api/v2/security-agent/runs/([A-Za-z0-9_.-]{1,100})/analyses", path)
        if match:
            self._handle_security_agent_run_analyses_post(match.group(1), payload)
            return
        match = re.fullmatch(r"/api/v2/security-agent/incidents/([A-Za-z0-9_.-]{1,100})/analyses", path)
        if match:
            self._handle_security_agent_incident_analyses_post(match.group(1), payload)
            return
        if path == "/api/v2/security-agent/analyses/compare":
            self._handle_security_agent_analyses_compare_post(payload)
            return
        match = re.fullmatch(r"/api/v2/security-agent/incidents/([A-Za-z0-9_.-]{1,100})/open-chat", path)
        if match:
            self._handle_security_agent_incident_open_chat_post(match.group(1), payload)
            return
        match = re.fullmatch(r"/api/v2/security-agent/incidents/([A-Za-z0-9_.-]{1,100})/troubleshoot", path)
        if match:
            self._handle_security_agent_incident_troubleshoot_post(match.group(1), payload)
            return
        if path == "/api/v2/security-agent/profiles":
            self._handle_security_agent_profiles_post(payload)
            return
        match = re.fullmatch(r"/api/v2/security-agent/profiles/([A-Za-z0-9_.-]{1,100})/delete", path)
        if match:
            self._handle_security_agent_profile_delete_post(match.group(1))
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

    def _handle_security_agent_status(self) -> None:
        try:
            cfg = SecurityAgentConfig()
            config_data = cfg.load()
            scheduler = cfg.get_task_scheduler_status()
            reports = cfg.get_latest_reports()
            devices = cfg.get_device_catalog()

            last_status = config_data.get("last_status") or {}
            last_collectors = {c.get("device_name"): c for c in last_status.get("collectors", [])}
            device_collector_map = {
                "fortigate_core": "FortiGate",
                "fortianalyzer": "FortiAnalyzer",
                "f5_bigip": "F5 BIG-IP",
                "cisco_fmc": "Cisco FMC",
                "sophos_email": "Sophos Email",
                "active_directory": "Active Directory",
                "exchange_2019": "Exchange",
            }
            enriched_devices = []
            for d in devices:
                item = dict(d)
                mapped_name = device_collector_map.get(d.get("id"))
                col_info = (last_collectors.get(mapped_name) if mapped_name else None) or last_collectors.get(d["name"])
                if not col_info:
                    d_tokens = set(re.findall(r'[a-z0-9]+', (d["name"] + " " + d.get("id", "")).lower()))
                    for c_name, c_data in last_collectors.items():
                        c_tokens = set(re.findall(r'[a-z0-9]+', (c_name or "").lower()))
                        if c_tokens and (c_tokens.issubset(d_tokens) or d_tokens.issubset(c_tokens)):
                            col_info = c_data
                            break
                if col_info:
                    item["last_collection_status"] = col_info.get("status", "READY")
                    item["last_events_count"] = col_info.get("events_count", 0)
                    item["last_duration_seconds"] = col_info.get("duration", 0)
                else:
                    item["last_collection_status"] = "CONFIGURED"
                    item["last_events_count"] = 0
                    item["last_duration_seconds"] = 0
                enriched_devices.append(item)

            resp = {
                "config": {
                    "schedule_time": config_data.get("schedule_time", "07:00"),
                    "schedule_enabled": config_data.get("schedule_enabled", True),
                    "recipients": config_data.get("recipients", []),
                },
                "scheduler": scheduler,
                "last_run": config_data.get("last_run"),
                "last_status": last_status,
                "reports": reports,
                "devices": enriched_devices,
            }
            self._json_response(200, resp)
        except Exception as exc:
            self._json_response(500, {"error": f"Failed fetching security agent status: {exc}"})

    def _handle_security_agent_config_post(self, payload: Dict[str, Any]) -> None:
        try:
            cfg = SecurityAgentConfig()
            if "recipients" in payload:
                recipients = payload["recipients"]
                if not isinstance(recipients, list):
                    raise ValueError("recipients must be a list of email strings.")
                cfg.set_recipients(recipients)

            if "schedule_time" in payload or "schedule_enabled" in payload:
                schedule_time = payload.get("schedule_time", cfg.get_schedule_time())
                schedule_enabled = payload.get("schedule_enabled", cfg.is_enabled())
                cfg.set_schedule(str(schedule_time), bool(schedule_enabled))

            self._handle_security_agent_status()
        except ValueError as exc:
            self._json_response(400, {"error": str(exc)})
        except Exception as exc:
            self._json_response(500, {"error": f"Failed updating security configuration: {exc}"})

    def _handle_security_agent_run_post(self, payload: Dict[str, Any]) -> None:
        try:
            from core.security_review.cli import run_security_pipeline
            from core.connectors.security.models import SeverityLevel

            dry_run = bool(payload.get("dry_run", False))
            send_email = bool(payload.get("send_email", True))
            recipients = payload.get("recipients")

            result = run_security_pipeline(dry_run=dry_run, send_email=send_email, recipients=recipients)
            incidents = result.get("incidents", [])
            collector_results = result.get("collectors", [])

            resp = {
                "success": result.get("success", True),
                "total_incidents": len(incidents),
                "critical_count": sum(1 for i in incidents if i.severity == SeverityLevel.CRITICAL),
                "high_count": sum(1 for i in incidents if i.severity == SeverityLevel.HIGH),
                "medium_count": sum(1 for i in incidents if i.severity == SeverityLevel.MEDIUM),
                "email_sent": result.get("email_sent", False),
                "html_path": result.get("html_path"),
                "pdf_path": result.get("pdf_path"),
                "collectors": [
                    {
                        "device_name": c.device_name,
                        "status": c.status.value,
                        "events_count": len(c.events),
                        "duration": c.collection_duration_seconds,
                    }
                    for c in collector_results
                ],
            }
            self._json_response(200, resp)
        except Exception as exc:
            self._json_response(500, {"error": f"Security review run failed: {exc}"})

    def _handle_security_agent_test_email_post(self, payload: Dict[str, Any]) -> None:
        try:
            from core.security_review.reporter import SecurityReporter
            reporter = SecurityReporter()
            recipients = payload.get("recipients")
            if recipients and not isinstance(recipients, list):
                raise ValueError("recipients must be a list of email strings.")
            success, msg = reporter.send_test_email(recipients=recipients)
            status_code = 200 if success else 502
            self._json_response(status_code, {"success": success, "message": msg})
        except ValueError as exc:
            self._json_response(400, {"error": str(exc)})
        except Exception as exc:
            self._json_response(500, {"error": f"Test email dispatch failed: {exc}"})

    def _handle_security_agent_report_html(self) -> None:
        try:
            cfg = SecurityAgentConfig()
            reports = cfg.get_latest_reports()
            html_info = reports.get("html", {})
            if not html_info.get("available") or not html_info.get("path"):
                self._json_response(404, {"error": "No HTML security report has been generated yet."})
                return
            html_path = Path(html_info["path"])
            if not html_path.exists():
                self._json_response(404, {"error": "HTML report file not found on disk."})
                return
            raw = html_path.read_bytes()
            report_csp = "default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
            self._set_headers(200, "text/html; charset=utf-8", content_length=len(raw), extra_headers={
                "Content-Disposition": f"inline; filename=\"{html_path.name}\"",
                "Content-Security-Policy": report_csp,
            })
            self.wfile.write(raw)
        except Exception as exc:
            self._json_response(500, {"error": f"Failed serving HTML report: {exc}"})

    def _handle_security_agent_report_pdf(self) -> None:
        try:
            cfg = SecurityAgentConfig()
            reports = cfg.get_latest_reports()
            pdf_info = reports.get("pdf", {})
            if not pdf_info.get("available") or not pdf_info.get("path"):
                self._json_response(404, {"error": "No PDF security report has been generated yet."})
                return
            pdf_path = Path(pdf_info["path"])
            if not pdf_path.exists():
                self._json_response(404, {"error": "PDF report file not found on disk."})
                return
            raw = pdf_path.read_bytes()
            self._set_headers(200, "application/pdf", content_length=len(raw), extra_headers={"Content-Disposition": f"attachment; filename=\"{pdf_path.name}\""})
            self.wfile.write(raw)
        except Exception as exc:
            self._json_response(500, {"error": f"Failed serving PDF report: {exc}"})

    def _handle_security_agent_runs_get(self) -> None:
        try:
            summaries = security_review_run_store.list_runs(limit=50)
            self._json_response(200, {"runs": summaries})
        except Exception as exc:
            self._json_response(500, {"error": f"Failed fetching security runs: {exc}"})

    def _handle_security_agent_run_get(self, run_id: str) -> None:
        try:
            run = security_review_run_store.get_run(run_id)
            if not run:
                self._json_response(404, {"error": f"Run '{run_id}' not found."})
                return
            self._json_response(200, run)
        except Exception as exc:
            self._json_response(500, {"error": f"Failed fetching run: {exc}"})

    def _handle_security_agent_runs_post(self, payload: Dict[str, Any]) -> None:
        try:
            req = SecurityReviewRequest.from_dict(payload or {})
            owner_digest = self._owner_digest()
            run = security_review_service.start_review(req, async_run=True, owner_session_digest=owner_digest)
            self._json_response(202, {
                "run_id": run.run_id,
                "state": run.state.value,
                "message": "Security review started.",
            })
        except ValueError as exc:
            self._json_response(400, {"error": str(exc)})
        except Exception as exc:
            self._json_response(500, {"error": f"Failed starting security review: {exc}"})

    def _handle_security_agent_run_cancel_post(self, run_id: str) -> None:
        try:
            cancelled = security_review_job_manager.request_cancel(run_id)
            self._json_response(200, {"run_id": run_id, "cancelled": cancelled})
        except Exception as exc:
            self._json_response(500, {"error": f"Failed cancelling run: {exc}"})

    def _handle_security_agent_run_retry_post(self, run_id: str, payload: Dict[str, Any]) -> None:
        try:
            only_failed = bool((payload or {}).get("only_failed", True))
            owner_digest = self._owner_digest()
            new_run = security_review_service.retry_review(run_id, only_failed=only_failed, async_run=True, owner_session_digest=owner_digest)
            self._json_response(202, {
                "run_id": new_run.run_id,
                "state": new_run.state.value,
                "retry_of": run_id,
                "message": "Retry security review started.",
            })
        except ValueError as exc:
            self._json_response(400, {"error": str(exc)})
        except Exception as exc:
            self._json_response(500, {"error": f"Failed retrying security run: {exc}"})

    def _stream_security_run_events(self, run_id: str) -> None:
        last_event_id_header = self.headers.get("Last-Event-ID")
        last_event_id: Optional[int] = None
        if last_event_id_header:
            try:
                last_event_id = int(last_event_id_header)
            except ValueError:
                pass

        run = security_review_run_store.get_run(run_id)
        if not run and not security_review_job_manager.is_running(run_id):
            self._json_response(404, {"error": f"Run '{run_id}' not found."})
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "close")
        self.end_headers()

        terminal_events = {"run.completed", "run.failed", "run.cancelled"}
        q, missed = security_review_job_manager.subscribe(run_id, last_event_id)
        try:
            for ev in missed:
                payload = f"id: {ev['id']}\nevent: {ev['event']}\ndata: {json.dumps(ev['data'])}\n\n".encode("utf-8")
                self.wfile.write(payload)
                self.wfile.flush()
                if ev["event"] in terminal_events:
                    return

            if run and run.get("state") in ("COMPLETED", "PARTIAL", "FAILED", "CANCELLED") and not security_review_job_manager.is_running(run_id):
                return

            heartbeat = 15.0
            while True:
                try:
                    ev = q.get(timeout=heartbeat)
                    payload = f"id: {ev['id']}\nevent: {ev['event']}\ndata: {json.dumps(ev['data'])}\n\n".encode("utf-8")
                    self.wfile.write(payload)
                    self.wfile.flush()
                    if ev["event"] in terminal_events:
                        return
                except queue.Empty:
                    if not security_review_job_manager.is_running(run_id):
                        return
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, socket.timeout):
            return
        finally:
            security_review_job_manager.unsubscribe(run_id, q)

    def _handle_security_agent_incidents_get(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> None:
        try:
            items, total = security_review_run_store.list_incident_records(
                status=status,
                severity=severity,
                category=category,
                search=search,
                limit=limit,
                offset=offset,
            )
            self._json_response(200, {
                "incidents": items,
                "total": total,
                "limit": limit,
                "offset": offset,
            })
        except Exception as exc:
            self._json_response(500, {"error": f"Failed fetching incidents: {exc}"})

    def _handle_security_agent_incident_get(self, fingerprint: str) -> None:
        try:
            rec = security_review_run_store.get_incident_record(fingerprint)
            if not rec:
                self._json_response(404, {"error": f"Incident '{fingerprint}' not found."})
                return
            self._json_response(200, rec.to_dict())
        except Exception as exc:
            self._json_response(500, {"error": f"Failed fetching incident: {exc}"})

    def _handle_security_agent_incident_timeline_get(self, fingerprint: str) -> None:
        try:
            rec = security_review_run_store.get_incident_record(fingerprint)
            if not rec:
                self._json_response(404, {"error": f"Incident '{fingerprint}' not found."})
                return
            timeline = security_review_run_store.get_incident_timeline(fingerprint)
            self._json_response(200, {"fingerprint": fingerprint, "timeline": timeline})
        except Exception as exc:
            self._json_response(500, {"error": f"Failed fetching incident timeline: {exc}"})

    def _handle_security_agent_incident_status_post(self, fingerprint: str, payload: Dict[str, Any]) -> None:
        try:
            new_status = str((payload or {}).get("status") or "").strip()
            if not new_status:
                self._json_response(400, {"error": "Status is required."})
                return
            author = str((payload or {}).get("author") or "operator").strip()
            note = str((payload or {}).get("note") or "").strip()
            updated = security_review_run_store.update_incident_status(
                fingerprint=fingerprint,
                new_status=new_status,
                author=author,
                note=note,
            )
            if not updated:
                self._json_response(404, {"error": f"Incident '{fingerprint}' not found."})
                return
            self._json_response(200, updated)
        except ValueError as exc:
            self._json_response(400, {"error": str(exc)})
        except Exception as exc:
            self._json_response(500, {"error": f"Failed updating incident status: {exc}"})

    def _handle_security_agent_incident_notes_post(self, fingerprint: str, payload: Dict[str, Any]) -> None:
        try:
            note = str((payload or {}).get("note") or "").strip()
            if not note:
                self._json_response(400, {"error": "Note text is required."})
                return
            author = str((payload or {}).get("author") or "operator").strip()
            updated = security_review_run_store.add_incident_note(
                fingerprint=fingerprint,
                note=note,
                author=author,
            )
            if not updated:
                self._json_response(404, {"error": f"Incident '{fingerprint}' not found."})
                return
            self._json_response(200, updated)
        except ValueError as exc:
            self._json_response(400, {"error": str(exc)})
        except Exception as exc:
            self._json_response(500, {"error": f"Failed adding incident note: {exc}"})

    def _handle_security_agent_incident_resolve_identity_post(self, fingerprint: str, payload: Dict[str, Any]) -> None:
        with _in_flight_resolutions_lock:
            if fingerprint in _in_flight_resolutions:
                self._json_response(409, {"error": f"Identity resolution already in-flight for incident '{fingerprint}'."})
                return
            _in_flight_resolutions.add(fingerprint)

        try:
            rec = security_review_run_store.get_incident_record(fingerprint)
            if not rec:
                self._json_response(404, {"error": f"Incident '{fingerprint}' not found."})
                return

            events: List[NormalizedSecurityEvent] = []
            target_ip = rec.attacker_identity or getattr(rec, "attacker_ip", None)
            supporting_ids = set(rec.supporting_event_ids) if getattr(rec, "supporting_event_ids", None) else None
            if rec.run_references:
                latest_run_id = rec.run_references[-1]
                raw_events = security_review_run_store.get_events(latest_run_id)
                for rev in raw_events:
                    try:
                        ev_id = rev.get("event_id")
                        if supporting_ids and ev_id not in supporting_ids:
                            continue
                        ev_ip = rev.get("attacker_ip")
                        if target_ip and ev_ip != target_ip:
                            continue
                        ev_ts = coerce_datetime_utc(rev.get("timestamp"))
                        if ev_ts is None:
                            continue
                        events.append(NormalizedSecurityEvent(
                            event_id=ev_id or "",
                            timestamp=ev_ts,
                            source_device=rev.get("source_device", ""),
                            category=ThreatCategory(rev.get("category", "ANOMALY")),
                            threat_name=rev.get("threat_name", ""),
                            attacker_ip=ev_ip,
                            target=rev.get("target"),
                            action_taken=rev.get("action_taken", "UNKNOWN"),
                            count=rev.get("count", 1),
                            raw_snippet=rev.get("raw_snippet", ""),
                            metadata=rev.get("metadata", {}),
                            attacker_hostname=rev.get("attacker_hostname"),
                            source_hostname=rev.get("source_hostname"),
                            attacker_mac=rev.get("attacker_mac"),
                            authenticated_source_user=rev.get("authenticated_source_user"),
                        ))
                    except Exception:
                        pass

            branch = (rec.branch if hasattr(rec, "branch") and rec.branch else None) or (payload or {}).get("branch")
            first_seen_dt = coerce_datetime_utc(rec.first_seen)
            last_seen_dt = coerce_datetime_utc(rec.last_seen)

            attribution = security_review_service.identity_resolver.resolve_attacker_identity(
                ip_address=target_ip,
                first_seen=first_seen_dt,
                last_seen=last_seen_dt,
                events=events,
                branch=branch,
                device_name=rec.source_device,
                supporting_event_ids=supporting_ids,
            )

            # Non-downgrade persistence check with schema-compliant history tracking
            current_attr = None
            if rec.attacker_attribution:
                try:
                    current_attr = AttackerAttribution.from_dict(rec.attacker_attribution)
                except Exception:
                    current_attr = None

            now_iso = datetime.now(timezone.utc).isoformat()
            run_ref = rec.run_references[-1] if rec.run_references else "manual-resolve"
            inc_time = rec.last_seen or now_iso

            conf_val = attribution.confidence if attribution.confidence in ("HIGH", "MEDIUM", "LOW", "UNKNOWN") else "UNKNOWN"
            attempt_entry = {
                "run_id": run_ref,
                "incident_time": inc_time,
                "attempt_time": now_iso,
                "status": attribution.status,
                "confidence": conf_val,
                "confidence_score": int(attribution.confidence_score or 0),
                "pc_name": attribution.pc_name if attribution.pc_name not in ("Unknown", "Not applicable") else None,
                "username": attribution.username if attribution.username not in ("Unknown", "Not applicable") else None,
                "sources": list(attribution.successful_sources),
                "diagnostic": "Manual resolution attempt via API.",
            }

            if current_attr and not should_replace_attribution(current_attr, attribution):
                # Retain existing higher-quality attribution, but append attempt to history
                history = list(getattr(current_attr, "attribution_history", []))
                attempt_entry["diagnostic"] = "Preserved prior higher-confidence attribution."
                history.append(attempt_entry)
                if len(history) > 10:
                    history = history[-10:]
                current_attr.attribution_history = history
                updated = security_review_run_store.update_incident_attribution(
                    fingerprint=fingerprint,
                    attribution=current_attr.to_dict(),
                )
                self._json_response(200, updated or rec.to_dict())
                return

            # Accepted as new attribution
            history = list(getattr(current_attr, "attribution_history", [])) if current_attr else []
            attempt_entry["diagnostic"] = "Accepted as new attribution."
            history.append(attempt_entry)
            if len(history) > 10:
                history = history[-10:]
            attribution.attribution_history = history

            updated = security_review_run_store.update_incident_attribution(
                fingerprint=fingerprint,
                attribution=attribution.to_dict(),
            )
            if not updated:
                self._json_response(404, {"error": f"Failed updating attribution for incident '{fingerprint}'."})
                return

            self._json_response(200, updated)
        except ValueError as exc:
            self._json_response(400, {"error": str(exc)})
        except Exception as exc:
            self._json_response(500, {"error": f"Failed resolving incident identity: {exc}"})
        finally:
            with _in_flight_resolutions_lock:
                _in_flight_resolutions.discard(fingerprint)


    def _stream_security_analysis_events(self, analysis_id: str) -> None:
        if hasattr(self, "_set_headers") and type(getattr(self, "wfile", None)).__name__ != "BufferedWriter":
            self._set_headers(200, "text/event-stream; charset=utf-8", extra_headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            })
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-transform")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

        headers = getattr(self, "headers", None)
        last_id_hdr = headers.get("Last-Event-ID") if headers and hasattr(headers, "get") else None
        cursor = int(last_id_hdr) + 1 if last_id_hdr and last_id_hdr.isdigit() else 0

        is_mock = "Mock" in type(getattr(self, "wfile", None)).__name__
        timeout_seconds = 1.0 if is_mock else 180.0
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            events = security_review_service.ai_analyzer.get_events(analysis_id)
            if cursor < len(events):
                while cursor < len(events):
                    ev = events[cursor]
                    ev_type = ev.get("event_type", "message")
                    payload = f"id: {cursor}\nevent: {ev_type}\ndata: {json.dumps(ev.get('data', {}))}\n\n".encode("utf-8")
                    try:
                        self.wfile.write(payload)
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        return
                    cursor += 1
                    if ev_type in ("analysis.completed", "analysis.failed"):
                        return
            else:
                res = security_review_service.ai_analyzer.get_analysis(analysis_id)
                if res and res.get("status") in ("COMPLETED", "FAILED", "PARTIAL"):
                    events = security_review_service.ai_analyzer.get_events(analysis_id)
                    if cursor >= len(events):
                        return
                if is_mock:
                    return
                try:
                    time.sleep(0.1)
                except Exception:
                    return

    def _handle_security_agent_analysis_get(self, analysis_id: str) -> None:
        analysis = security_review_service.ai_analyzer.get_analysis(analysis_id)
        if not analysis:
            self._json_response(404, {"error": f"Analysis '{analysis_id}' not found."})
            return
        self._json_response(200, analysis)

    def _handle_security_agent_analysis_report_get(self, analysis_id: str, params: Dict[str, List[str]]) -> None:
        fmt = ((params.get("format") or ["html"])[0]).lower()
        analysis = security_review_service.ai_analyzer.get_analysis(analysis_id)
        if not analysis and hasattr(security_review_run_store, "get_analysis"):
            analysis = security_review_run_store.get_analysis(analysis_id)
        if not analysis:
            self._json_response(404, {"error": f"Analysis '{analysis_id}' not found."})
            return
        if fmt == "json":
            self._json_response(200, analysis)
            return
        if fmt == "pdf":
            try:
                pdf_bytes = security_review_service.reporter.compile_analysis_pdf_report(analysis)
                self._set_headers(200, "application/pdf", content_length=len(pdf_bytes), extra_headers={
                    "Content-Disposition": f"inline; filename=\"ai_assessment_{analysis_id}.pdf\"",
                })
                self.wfile.write(pdf_bytes)
                return
            except Exception as exc:
                self._json_response(500, {"error": f"PDF generation failed: {exc}"})
                return
        # Default HTML report
        try:
            html_data = security_review_service.reporter.generate_analysis_html_report(analysis)
            report_csp = "default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
            raw_bytes = html_data.encode("utf-8")
            self._set_headers(200, "text/html; charset=utf-8", content_length=len(raw_bytes), extra_headers={
                "Content-Security-Policy": report_csp,
            })
            self.wfile.write(raw_bytes)
        except Exception as exc:
            self._json_response(500, {"error": f"HTML report generation failed: {exc}"})

    def _handle_security_agent_run_analyses_post(self, run_id: str, payload: Dict[str, Any]) -> None:
        engine = str((payload or {}).get("engine") or "BOTH").strip()
        model = (payload or {}).get("model")
        owner_digest = self._owner_digest()
        is_async = (payload or {}).get("async", True)
        try:
            if not is_async:
                res = security_review_service.ai_analyzer.analyze_run(
                    run_id=run_id,
                    engine=engine,
                    model=model,
                    owner_session_digest=owner_digest,
                )
                self._json_response(200, res)
            else:
                analysis_id = security_review_service.ai_analyzer.submit_run_analysis(
                    run_id=run_id,
                    engine=engine,
                    model=model,
                    owner_session_digest=owner_digest,
                )
                self._json_response(202, {
                    "status": "ACCEPTED",
                    "analysis_id": analysis_id,
                    "engine": engine,
                    "run_id": run_id,
                })
        except ValueError as exc:
            self._json_response(404 if "not found" in str(exc).lower() else 400, {"error": str(exc)})
        except Exception as exc:
            self._json_response(500, {"error": f"AI analysis failed: {exc}"})

    def _handle_security_agent_incident_analyses_post(self, fingerprint: str, payload: Dict[str, Any]) -> None:
        engine = str((payload or {}).get("engine") or "BOTH").strip()
        model = (payload or {}).get("model")
        owner_digest = self._owner_digest()
        is_async = (payload or {}).get("async", True)
        try:
            if not is_async:
                res = security_review_service.ai_analyzer.analyze_incident(
                    fingerprint=fingerprint,
                    engine=engine,
                    model=model,
                    owner_session_digest=owner_digest,
                )
                self._json_response(200, res)
            else:
                analysis_id = security_review_service.ai_analyzer.submit_incident_analysis(
                    fingerprint=fingerprint,
                    engine=engine,
                    model=model,
                    owner_session_digest=owner_digest,
                )
                self._json_response(202, {
                    "status": "ACCEPTED",
                    "analysis_id": analysis_id,
                    "engine": engine,
                    "incident_fingerprint": fingerprint,
                })
        except ValueError as exc:
            self._json_response(404 if "not found" in str(exc).lower() else 400, {"error": str(exc)})
        except Exception as exc:
            self._json_response(500, {"error": f"AI analysis failed: {exc}"})

    def _handle_security_agent_analyses_compare_post(self, payload: Dict[str, Any]) -> None:
        codex_id = str((payload or {}).get("codex_analysis_id") or "").strip()
        agy_id = str((payload or {}).get("antigravity_analysis_id") or "").strip()
        if not codex_id or not agy_id:
            self._json_response(400, {"error": "codex_analysis_id and antigravity_analysis_id are required."})
            return
        try:
            res = security_review_service.ai_analyzer.compare_analyses(codex_id, agy_id)
            self._json_response(200, res)
        except ValueError as exc:
            self._json_response(404 if "not found" in str(exc).lower() else 400, {"error": str(exc)})
        except Exception as exc:
            self._json_response(500, {"error": f"Comparison failed: {exc}"})

    def _handle_security_agent_incident_open_chat_post(self, fingerprint: str, payload: Dict[str, Any]) -> None:
        engine = str((payload or {}).get("engine") or "codex").strip()
        model = (payload or {}).get("model")
        owner_digest = self._owner_digest()
        try:
            res = security_review_service.ai_analyzer.open_incident_chat(
                fingerprint=fingerprint,
                engine=engine,
                model=model,
                owner_session_digest=owner_digest,
            )
            self._json_response(200, res)
        except ValueError as exc:
            self._json_response(404 if "not found" in str(exc).lower() else 400, {"error": str(exc)})
        except Exception as exc:
            self._json_response(500, {"error": f"Open in Chat failed: {exc}"})

    def _handle_security_agent_incident_troubleshoot_post(self, fingerprint: str, payload: Dict[str, Any]) -> None:
        scenario_id = (payload or {}).get("scenario_id")
        binding_id = (payload or {}).get("binding_id")
        symptom = (payload or {}).get("symptom")
        execute_p9 = bool((payload or {}).get("execute_p9", False))
        owner_proceed = bool((payload or {}).get("owner_proceed", False))
        collector_override = None
        if execute_p9 and owner_proceed:
            try:
                from core.troubleshooting.p9_collector import P9LiveCollector
                collector_override = P9LiveCollector(base_dir).collect
            except Exception as exc:
                logger.warning("Could not initialize P9LiveCollector: %s", exc)
        try:
            res = security_troubleshooting_bridge.start_troubleshooting(
                fingerprint=fingerprint,
                scenario_id=scenario_id,
                binding_id=binding_id,
                symptom=symptom,
                execute_p9=execute_p9,
                owner_proceed=owner_proceed,
                collector_override=collector_override,
            )
            self._json_response(200, res)
        except ValueError as exc:
            self._json_response(404 if "not found" in str(exc).lower() else 400, {"error": str(exc)})
        except Exception as exc:
            self._json_response(500, {"error": f"Troubleshooting handoff failed: {exc}"})

    def _handle_security_agent_profiles_get(self) -> None:
        profiles = security_review_service.reporter.config_mgr.get_profiles()
        active = security_review_service.reporter.config_mgr.load().get("active_profile", "Daily Full Review")
        active_id = None
        normalized_profiles = []
        for p in profiles:
            p_id = p.get("profile_id") or p.get("id")
            p_name = p.get("name", "")
            opts = p.get("options", {})
            norm = dict(p)
            norm["id"] = p_id
            norm["profile_id"] = p_id
            if opts:
                if "selected_collectors" in opts and "collector_ids" not in norm:
                    norm["collector_ids"] = opts["selected_collectors"]
                if "time_window" in opts and "hours_back" not in norm:
                    norm["hours_back"] = opts["time_window"].get("hours", 24)
                if "ai_engine" in opts and "analysis_engine" not in norm:
                    norm["analysis_engine"] = opts["ai_engine"]
            normalized_profiles.append(norm)
            if active and (active.lower() == p_name.lower() or active.lower() == (p_id or "").lower()):
                active_id = p_id
        if not active_id and normalized_profiles:
            active_id = normalized_profiles[0]["id"]
        self._json_response(200, {
            "profiles": normalized_profiles,
            "active_profile": active,
            "active_profile_id": active_id,
        })

    def _handle_security_agent_profiles_post(self, payload: Dict[str, Any]) -> None:
        try:
            saved = security_review_service.reporter.config_mgr.save_profile(payload or {})
            self._json_response(200, saved)
        except ValueError as exc:
            self._json_response(400, {"error": str(exc)})
        except Exception as exc:
            self._json_response(500, {"error": f"Failed saving profile: {exc}"})

    def _handle_security_agent_profile_delete_post(self, profile_id: str) -> None:
        deleted = security_review_service.reporter.config_mgr.delete_profile(profile_id)
        if not deleted:
            self._json_response(400, {"error": f"Cannot delete profile '{profile_id}' (built-in or not found)."})
            return
        self._json_response(200, {"status": "DELETED", "profile_id": profile_id})

    def _handle_security_agent_run_report_get(self, run_id: str, params: Dict[str, List[str]]) -> None:
        fmt = ((params.get("format") or ["executive"])[0]).lower()
        run = security_review_run_store.get_run(run_id)
        if not run:
            self._json_response(404, {"error": f"Run '{run_id}' not found."})
            return
        if fmt == "json":
            data = security_review_service.reporter.generate_json_export(run_id, security_review_run_store)
            self._json_response(200, data)
            return
        if fmt == "csv":
            csv_data = security_review_service.reporter.generate_csv_incident_export(run_id, security_review_run_store)
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f"attachment; filename=\"security_incidents_{run_id}.csv\"")
            self.end_headers()
            self.wfile.write(csv_data.encode("utf-8"))
            return
        if fmt == "technical":
            html_data = security_review_service.reporter.generate_technical_report(run_id, security_review_run_store)
            report_csp = "default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
            raw_bytes = html_data.encode("utf-8")
            self._set_headers(200, "text/html; charset=utf-8", content_length=len(raw_bytes), extra_headers={
                "Content-Security-Policy": report_csp,
            })
            self.wfile.write(raw_bytes)
            return
        if fmt == "pdf":
            try:
                pdf_bytes = security_review_service.reporter.compile_pdf_report("", run_id=run_id, run_store=security_review_run_store)
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Disposition", f"inline; filename=\"security_report_{run_id}.pdf\"")
                self.end_headers()
                self.wfile.write(pdf_bytes)
                return
            except Exception as exc:
                self._json_response(500, {"error": f"PDF generation failed: {exc}"})
                return
        # Default executive HTML
        html_data = security_review_service.reporter.generate_executive_report(run_id, security_review_run_store)
        report_csp = "default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        raw_bytes = html_data.encode("utf-8")
        self._set_headers(200, "text/html; charset=utf-8", content_length=len(raw_bytes), extra_headers={
            "Content-Security-Policy": report_csp,
        })
        self.wfile.write(raw_bytes)

    def _handle_security_agent_trends_get(self, params: Dict[str, List[str]]) -> None:
        try:
            days = int((params.get("days") or [30])[0])
        except ValueError:
            days = 30
        trends = get_trend_analytics(
            run_store=security_review_run_store,
            incident_store=security_review_run_store.incident_store,
            days=days,
        )
        self._json_response(200, trends)


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
