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
import yaml
import jsonschema
import urllib.parse
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
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
from core.runbooks.registry import RunbookRegistry
from core.llm.chatgpt_oauth import ChatGPTOAuthEngine
from core.observability.tracer import ObservabilityTracer
from integrations.n8n.webhook_listener import WebhookAlertListener

keys_storage_file = base_dir / "config" / "api_keys_storage.json"

def load_persistent_keys():
    if keys_storage_file.exists():
        try:
            with open(keys_storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    if v:
                        os.environ[k] = v
        except Exception:
            pass

def save_persistent_keys(keys_dict: Dict[str, str]):
    existing = {}
    if keys_storage_file.exists():
        try:
            with open(keys_storage_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}
    for k, v in keys_dict.items():
        if v:
            existing[k] = v
            os.environ[k] = v
    keys_storage_file.parent.mkdir(parents=True, exist_ok=True)
    with open(keys_storage_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

load_persistent_keys()

class MNEBrainAPIHandler(BaseHTTPRequestHandler):
    gui_dir = base_dir / "gui"

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

    def _set_headers(self, status_code: int = 200, content_type: str = "application/json"):
        self.send_response(status_code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(204)

    def _read_json_body(self) -> Dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 0:
                raw_body = self.rfile.read(length).decode("utf-8")
                return json.loads(raw_body)
        except Exception:
            pass
        return {}

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
                    with open(file_path, "rb") as f:
                        self._set_headers(200, ct)
                        self.wfile.write(f.read())
                    return
                except Exception:
                    pass

        # REST API Endpoints
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
        elif path == "/api/oauth/chatgpt/url":
            self._handle_oauth_url()
        elif path == "/api/oauth/chatgpt/status":
            self._handle_oauth_status()
        elif path == "/api/oauth/callback" or path == "/auth/callback":
            self._handle_oauth_callback(params)
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
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": f"Endpoint {path} not found"}).encode("utf-8"))

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        body = self._read_json_body()

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
        elif path == "/api/oauth/chatgpt/token":
            self._handle_oauth_token(body)
        elif path == "/api/settings":
            self._handle_settings_post(body)
        elif path == "/api/settings/auto":
            self._handle_settings_auto()
        elif path == "/api/troubleshooting/p8/plan":
            self._handle_p8_plan(body)
        elif path == "/api/troubleshooting/p9/plan":
            self._handle_p9_plan(body)
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": f"Endpoint {path} not found"}).encode("utf-8"))

    # Handler Implementation Methods
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
        def mask_key(k_name):
            val = os.getenv(k_name, "")
            if not val:
                return "NOT_CONFIGURED"
            return f"CONFIGURED ({val[:4]}...{val[-4:] if len(val)>8 else ''})"

        res = {
            "llm_provider": os.getenv("LLM_PROVIDER", "local_fallback"),
            "evidence_token_limit": 1500,
            "policy_enforcement": "STRICT",
            "zero_auto_overwrite": True,
            "api_keys": {
                "OPENAI_API_KEY": mask_key("OPENAI_API_KEY"),
                "ANTHROPIC_API_KEY": mask_key("ANTHROPIC_API_KEY"),
                "DEEPSEEK_API_KEY": mask_key("DEEPSEEK_API_KEY"),
                "GEMINI_API_KEY": mask_key("GEMINI_API_KEY")
            },
            "base_urls": {
                "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "ANTHROPIC_BASE_URL": os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
                "DEEPSEEK_BASE_URL": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
                "GEMINI_BASE_URL": os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
            },
            "credentials_status": {
                "FORTIGATE_SSH": "CONFIGURED" if os.getenv("FORTIGATE_SSH_USER") else "NOT_CONFIGURED",
                "CISCO_SSH": "CONFIGURED" if os.getenv("SSH_USER") else "NOT_CONFIGURED",
                "VMWARE_VCENTER": "CONFIGURED" if os.getenv("VMWARE_VCENTER_USER") else "NOT_CONFIGURED",
                "WINRM": "CONFIGURED" if os.getenv("WINRM_USER") else "NOT_CONFIGURED"
            }
        }
        self._set_headers(200)
        self.wfile.write(json.dumps(res, indent=2).encode("utf-8"))

    def _handle_settings_post(self, body: Dict[str, Any]):
        provider = body.get("llm_provider")
        if provider:
            os.environ["LLM_PROVIDER"] = provider

        to_save = {}
        if body.get("openai_api_key"):
            to_save["OPENAI_API_KEY"] = body["openai_api_key"]
        if body.get("openai_base_url"):
            to_save["OPENAI_BASE_URL"] = body["openai_base_url"]

        if body.get("anthropic_api_key"):
            to_save["ANTHROPIC_API_KEY"] = body["anthropic_api_key"]
        if body.get("anthropic_base_url"):
            to_save["ANTHROPIC_BASE_URL"] = body["anthropic_base_url"]

        if body.get("deepseek_api_key"):
            to_save["DEEPSEEK_API_KEY"] = body["deepseek_api_key"]

        if body.get("gemini_api_key"):
            to_save["GEMINI_API_KEY"] = body["gemini_api_key"]
        if body.get("gemini_base_url"):
            to_save["GEMINI_BASE_URL"] = body["gemini_base_url"]

        save_persistent_keys(to_save)

        self._set_headers(200)
        self.wfile.write(json.dumps({
            "status": "UPDATED",
            "llm_provider": os.getenv("LLM_PROVIDER"),
            "message": "LLM Provider and API Credentials updated successfully."
        }).encode("utf-8"))

    def _handle_settings_auto(self):
        # Auto-detect best available credentials
        provider = "local_fallback"
        msg = "Auto-configured Local Fallback Mode."

        if os.getenv("OPENAI_API_KEY"):
            provider = "openai"
            msg = "Auto-configured OpenAI API (GPT-4o) using OPENAI_API_KEY."
        elif os.getenv("CHATGPT_OAUTH_ACCESS_TOKEN"):
            provider = "chatgpt_oauth"
            msg = "Auto-configured ChatGPT Account OAuth Token."
        elif os.getenv("ANTHROPIC_API_KEY"):
            provider = "anthropic"
            msg = "Auto-configured Anthropic API using ANTHROPIC_API_KEY."
        elif os.getenv("DEEPSEEK_API_KEY"):
            provider = "deepseek"
            msg = "Auto-configured DeepSeek API."

        os.environ["LLM_PROVIDER"] = provider
        self._set_headers(200)
        self.wfile.write(json.dumps({
            "status": "SUCCESS",
            "llm_provider": provider,
            "message": msg
        }).encode("utf-8"))

    def _handle_oauth_url(self):
        oauth_engine = ChatGPTOAuthEngine(base_dir=base_dir)
        info = oauth_engine.get_authorization_url()
        self._set_headers(200)
        self.wfile.write(json.dumps(info, indent=2).encode("utf-8"))

    def _handle_oauth_status(self):
        oauth_engine = ChatGPTOAuthEngine(base_dir=base_dir)
        token = oauth_engine.get_access_token()
        res = {
            "status": "CONNECTED" if token else "NOT_CONNECTED",
            "access_token": f"{token[:8]}...{token[-6:]}" if token and len(token)>14 else ("CONFIGURED" if token else None)
        }
        self._set_headers(200)
        self.wfile.write(json.dumps(res, indent=2).encode("utf-8"))

    def _handle_oauth_token(self, body: Dict[str, Any]):
        oauth_engine = ChatGPTOAuthEngine(base_dir=base_dir)
        code = body.get("code")
        verifier = body.get("code_verifier")
        token = body.get("access_token")

        if token:
            oauth_engine.save_tokens({"access_token": token, "token_type": "Bearer", "source": "User Registered ChatGPT Account Token"})
            os.environ["LLM_PROVIDER"] = "chatgpt_oauth"
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "SUCCESS", "message": "ChatGPT Account OAuth Token Registered Successfully."}).encode("utf-8"))
        elif code and verifier:
            res = oauth_engine.exchange_code_for_token(code, verifier)
            os.environ["LLM_PROVIDER"] = "chatgpt_oauth"
            self._set_headers(200)
            self.wfile.write(json.dumps(res, indent=2).encode("utf-8"))
    def _handle_oauth_callback(self, params: Dict[str, Any]):
        codes = params.get("code", [])
        code = codes[0] if codes else None
        if code:
            oauth_engine = ChatGPTOAuthEngine(base_dir=base_dir)
            oauth_engine.save_tokens({
                "access_token": f"chatgpt-oauth-code-{code[:12]}",
                "code": code,
                "token_type": "Bearer",
                "source": "ChatGPT OAuth Callback Code Authorized"
            })
            os.environ["LLM_PROVIDER"] = "chatgpt_oauth"

        self.send_response(302)
        self.send_header("Location", "/?oauth=success")
        self.end_headers()

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

    def _handle_settings_post(self, body: Dict[str, Any]):
        provider = body.get("llm_provider")
        if provider:
            os.environ["LLM_PROVIDER"] = provider
        self._set_headers(200)
        self.wfile.write(json.dumps({"status": "UPDATED", "llm_provider": os.getenv("LLM_PROVIDER")}).encode("utf-8"))

def run_api_server(port: int = 8080):
    import threading

    # Start background listener on port 1455 for ChatGPT OAuth redirect callbacks
    def start_oauth_port_1455():
        try:
            srv1455 = HTTPServer(("", 1455), MNEBrainAPIHandler)
            print("ChatGPT OAuth Redirect Callback Listener active on port 1455...")
            srv1455.serve_forever()
        except Exception:
            pass

    t1455 = threading.Thread(target=start_oauth_port_1455, daemon=True)
    t1455.start()

    ports_to_try = [port, 8080, 8088, 8085, 8090]
    bound_server = None
    selected_port = port

    for p in ports_to_try:
        try:
            server_address = ("", p)
            bound_server = HTTPServer(server_address, MNEBrainAPIHandler)
            selected_port = p
            break
        except Exception:
            continue

    if bound_server:
        print(f"MNE_Brain Release 2 REST API Server running on port {selected_port}...")
        bound_server.serve_forever()
    else:
        print("ERROR: Could not bind API Server to any available port.")

if __name__ == "__main__":
    run_api_server()
