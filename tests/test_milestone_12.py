#!/usr/bin/env python3
"""Offline validation for the read-only presentation console boundary."""

import inspect
import io
import json
import re
import sys
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.api import server as api_server


def test_milestone_12() -> bool:
    print("[VALIDATING MILESTONE 12 PRESENTATION GUI]")
    errors: list[str] = []
    passed = 0

    gui_dir = base_dir / "gui"
    html_file = gui_dir / "index.html"
    server_file = gui_dir / "server.py"
    html_text = html_file.read_text(encoding="utf-8") if html_file.exists() else ""
    server_text = server_file.read_text(encoding="utf-8") if server_file.exists() else ""

    required_views = {"thread-list", "message-stream", "composer", "evidence-sources", "tool-drawer", "settings-panel", "provider-select", "permission-mode"}
    if (
        "MNE_Brain Release 2" in html_text
        and "ZERO Business Logic in GUI" in html_text
        and all(f'id="{view_id}"' in html_text for view_id in required_views)
        and "viewport" in html_text
    ):
        print(" [PASS] Responsive evidence-console views and architecture notice are present")
        passed += 1
    else:
        errors.append("GUI structure or required presentation views are incomplete")

    scripts = "\n".join(path.read_text(encoding="utf-8") for path in sorted((gui_dir / "scripts").glob("*.js")))
    forbidden_gui_capabilities = {"innerHTML": "unsafe dynamic HTML insertion", "command_hash": "command hash calculation", "expected_approval_phrase": "approval phrase calculation", "sha256": "approval digest calculation"}
    found_capabilities = [label for marker, label in forbidden_gui_capabilities.items() if marker in scripts]
    required_modules = {"api.js", "auth.js", "threads.js", "composer.js", "streaming.js", "activity.js", "evidence.js", "tool_calls.js", "approvals.js", "providers.js", "p10.js"}
    if (
        not found_capabilities
        and {path.name for path in (gui_dir / "scripts").glob("*.js")} == required_modules
        and "type=\"module\"" in html_text
        and "X-CSRF-Token" in scripts
        and "textContent" in scripts
        and "crypto.randomUUID" in scripts
        and "unsafe-inline" not in html_text
    ):
        print(" [PASS] Modular GUI presents server-built risk and approval state without calculating hashes, phrases, or commands")
        passed += 1
    else:
        errors.append(f"GUI presentation boundary failed: found={found_capabilities}")

    misleading_claims = [
        "LEVEL 5 TRUST",
        "verified via Level 5 Live Telemetry",
        "Brain Active",
        "Active Operational Alerts",
        "Government Enterprise NOC Staging",
        "FortiGate port2 secondary ISP link down",
    ]
    if not any(claim in html_text for claim in misleading_claims) and "Development console only" in html_text:
        print(" [PASS] Static simulated health, alert, and verification claims were removed")
        passed += 1
    else:
        errors.append("GUI still contains simulated or unsupported operational claims")

    forbidden_imports = ["core.router", "core.reasoning", "core.policy", "core.execution", "core.remediation"]
    imported_logic = [name for name in forbidden_imports if name in server_text]
    if (
        "ZERO Business Logic in GUI" in server_text
        and "from core.api.server import run_api_server" in server_text
        and not imported_logic
    ):
        print(" [PASS] Presentation server delegates to the API without importing decision engines")
        passed += 1
    else:
        errors.append(f"Presentation-server boundary failed: imports={imported_logic}")

    handler = object.__new__(api_server.MNEBrainAPIHandler)
    handler.gui_dir = gui_dir
    if (
        handler._resolve_gui_asset("/") == html_file.resolve()
        and handler._resolve_gui_asset("/index.html") == html_file.resolve()
        and handler._resolve_gui_asset("/../config/api_keys_storage.json") is None
        and handler._resolve_gui_asset("/%2e%2e/config/api_keys_storage.json") is None
        and handler._resolve_gui_asset("/../knowledge/network/core.md") is None
    ):
        print(" [PASS] Static asset resolution is contained to the GUI directory")
        passed += 1
    else:
        errors.append("Static-file containment failed")

    dashboard_handler = object.__new__(api_server.MNEBrainAPIHandler)
    dashboard_handler.wfile = io.BytesIO()
    dashboard_statuses: list[int] = []
    dashboard_handler._set_headers = lambda status_code=200, content_type="application/json": dashboard_statuses.append(status_code)
    dashboard_handler._handle_dashboard()
    dashboard = json.loads(dashboard_handler.wfile.getvalue().decode("utf-8"))
    dashboard_source = inspect.getsource(api_server.MNEBrainAPIHandler._handle_dashboard)
    truthful_dashboard = (
        dashboard_statuses == [200]
        and dashboard["status"] == "DEVELOPMENT_ONLY"
        and dashboard["operational_ready"] is False
        and dashboard["live_verification"] == "NOT_CONFIGURED"
        and dashboard["alert_ingestion"] == "DISABLED_BY_POLICY"
        and dashboard["active_alerts"] == []
        and dashboard["runbooks"] == 12
        and dashboard["operational_runbook_coverage_percent"] == 100.0
        and dashboard["operational_runbook_readiness"] is True
        and dashboard["connector_families"] == 15
        and dashboard["offline_connector_coverage_percent"] == 100.0
        and dashboard["offline_connector_readiness"] is True
        and dashboard["live_transport_coverage_percent"] == 2.08
        and set(dashboard["driver_statuses"].values()) == {"PLANNING_ONLY_NOT_CONFIGURED"}
        and "execute_command" not in dashboard_source
        and "DriverFactory" not in dashboard_source
    )
    if truthful_dashboard:
        print(" [PASS] Dashboard API returns truthful offline capability state without driver calls")
        passed += 1
    else:
        errors.append(f"Dashboard truthfulness boundary failed: {dashboard}")

    runbook_handler = object.__new__(api_server.MNEBrainAPIHandler)
    runbook_handler.wfile = io.BytesIO()
    runbook_statuses: list[int] = []
    runbook_handler._set_headers = lambda status_code=200, content_type="application/json": runbook_statuses.append(status_code)
    runbook_handler._handle_runbooks({})
    runbooks = json.loads(runbook_handler.wfile.getvalue().decode("utf-8"))
    if (
        runbook_statuses == [200]
        and runbooks["total_runbooks"] == 12
        and runbooks["coverage"]["operational_coverage_percent"] == 100.0
        and runbooks["coverage"]["production_readiness_claimed"] is False
        and runbooks["body_included"] is False
        and runbooks["live_connection_attempted"] is False
        and runbooks["persistence_attempted"] is False
        and runbooks["remediation_attempted"] is False
        and all("body" not in item for item in runbooks["runbooks"])
    ):
        print(" [PASS] Runbook API exposes reviewed metadata and coverage without bodies or side effects")
        passed += 1
    else:
        errors.append(f"Runbook API boundary failed: {runbooks}")

    connector_handler = object.__new__(api_server.MNEBrainAPIHandler)
    connector_handler.wfile = io.BytesIO()
    connector_statuses: list[int] = []
    connector_handler._set_headers = lambda status_code=200, content_type="application/json": connector_statuses.append(status_code)
    connector_handler._handle_connectors({})
    connectors = json.loads(connector_handler.wfile.getvalue().decode("utf-8"))
    serialized_connectors = json.dumps(connectors, sort_keys=True).casefold()
    if (
        connector_statuses == [200]
        and connectors["total_connectors"] == 15
        and connectors["coverage"]["offline_validation_coverage_percent"] == 100.0
        and connectors["coverage"]["live_transport_entities"] == 1
        and connectors["coverage"]["production_readiness_claimed"] is False
        and connectors["live_collection_enabled"] is False
        and connectors["live_connection_attempted"] is False
        and connectors["persistence_attempted"] is False
        and connectors["remediation_attempted"] is False
        and connectors["operations_included"] is False
        and not any(marker in serialized_connectors for marker in ("credential_reference", "raw_output", "172.23."))
    ):
        print(" [PASS] Connector API exposes offline readiness without operations, secrets, or side effects")
        passed += 1
    else:
        errors.append(f"Connector API boundary failed: {connectors}")

    header_source = inspect.getsource(api_server.MNEBrainAPIHandler._set_headers)
    required_headers = ["Content-Security-Policy", "X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy"]
    if all(header in header_source for header in required_headers):
        print(" [PASS] Browser responses declare baseline content and framing protections")
        passed += 1
    else:
        errors.append("Required browser response protections are missing")

    print("\n--- MILESTONE 12 VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for error in errors:
            print(f" - {error}")
        return False
    print(f"SUCCESS: {passed} Presentation GUI Components Verified (0 Errors)")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_milestone_12() else 1)
