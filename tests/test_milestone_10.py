#!/usr/bin/env python3
"""Offline validation for authenticated, non-executing alert ingestion."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from integrations.n8n.webhook_listener import WebhookAlertListener


REFERENCE_TIME = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)


def _alert(event_id: str = "evt-001") -> dict[str, str]:
    return {
        "event_id": event_id,
        "source": "Prometheus",
        "alert_name": "High CPU utilization on test firewall",
        "host": "192.0.2.10",
        "severity": "WARNING",
        "occurred_at": REFERENCE_TIME.isoformat(),
    }


def test_milestone_10() -> bool:
    print("[VALIDATING MILESTONE 10 ALERT INGESTION FOUNDATION]")
    errors: list[str] = []
    passed = 0

    disabled_listener = WebhookAlertListener(base_dir=base_dir)
    disabled = disabled_listener.process_alert_payload(
        _alert(),
        authenticated=True,
        authentication_reference="auth-test-01",
        now=REFERENCE_TIME,
    )
    if (
        disabled["status"] == "INGESTION_DISABLED"
        and not disabled["accepted"]
        and disabled["investigation_request"] is None
    ):
        print(" [PASS] Repository policy disables webhook ingestion by default")
        passed += 1
    else:
        errors.append(f"Default ingestion gate failed: {disabled}")

    listener = WebhookAlertListener(base_dir=base_dir, ingestion_enabled=True)
    unauthenticated = listener.process_alert_payload(_alert(), now=REFERENCE_TIME)
    if (
        unauthenticated["status"] == "UNAUTHENTICATED"
        and not unauthenticated["accepted"]
    ):
        print(" [PASS] Enabled ingestion still requires an authentication reference")
        passed += 1
    else:
        errors.append(f"Authentication gate failed: {unauthenticated}")

    accepted = listener.process_alert_payload(
        _alert(),
        authenticated=True,
        authentication_reference="auth-test-01",
        now=REFERENCE_TIME,
    )
    request = accepted.get("investigation_request") or {}
    constraints = request.get("constraints") or {}
    if (
        accepted["status"] == "ACCEPTED_FOR_POLICY_REVIEW"
        and accepted["next_action"] == "POLICY_REVIEW_REQUIRED"
        and request.get("target") == "192.0.2.10"
        and request.get("source") == "prometheus"
        and constraints.get("read_only") is True
        and constraints.get("automatic_execution_allowed") is False
        and constraints.get("automatic_remediation_allowed") is False
        and "generated_query" not in accepted
    ):
        print(" [PASS] Accepted alert becomes a structured, non-executing policy-review request")
        passed += 1
    else:
        errors.append(f"Alert normalization failed: {accepted}")

    duplicate = listener.process_alert_payload(
        _alert(),
        authenticated=True,
        authentication_reference="auth-test-02",
        now=REFERENCE_TIME,
    )
    stale_payload = _alert("evt-stale")
    stale_payload["occurred_at"] = (REFERENCE_TIME - timedelta(minutes=10)).isoformat()
    stale = listener.process_alert_payload(
        stale_payload,
        authenticated=True,
        authentication_reference="auth-test-03",
        now=REFERENCE_TIME,
    )
    if duplicate["status"] == "DUPLICATE_EVENT" and stale["status"] == "STALE_EVENT":
        print(" [PASS] In-memory replay protection and freshness windows reject duplicate or stale alerts")
        passed += 1
    else:
        errors.append(f"Replay/freshness handling failed: duplicate={duplicate}, stale={stale}")

    disallowed_source_payload = _alert("evt-source")
    disallowed_source_payload["source"] = "UnknownMonitor"
    invalid_target_payload = _alert("evt-target")
    invalid_target_payload["host"] = "host; invoke-remediation"
    invalid_severity_payload = _alert("evt-severity")
    invalid_severity_payload["severity"] = "EMERGENCY"
    validation_results = [
        listener.process_alert_payload(
            payload,
            authenticated=True,
            authentication_reference=f"auth-validation-{index}",
            now=REFERENCE_TIME,
        )
        for index, payload in enumerate(
            (disallowed_source_payload, invalid_target_payload, invalid_severity_payload), start=1
        )
    ]
    if [result["status"] for result in validation_results] == [
        "SOURCE_NOT_ALLOWED",
        "INVALID_TARGET",
        "INVALID_SEVERITY",
    ]:
        print(" [PASS] Source, target, and severity allowlists fail closed")
        passed += 1
    else:
        errors.append(f"Payload validation failed: {validation_results}")

    oversized = _alert("evt-large")
    oversized["alert_name"] = "x" * 9000
    oversized_result = listener.process_alert_payload(
        oversized,
        authenticated=True,
        authentication_reference="auth-test-large",
        now=REFERENCE_TIME,
    )
    if oversized_result["status"] == "PAYLOAD_TOO_LARGE":
        print(" [PASS] Oversized payloads are rejected before normalization")
        passed += 1
    else:
        errors.append(f"Payload size boundary failed: {oversized_result}")

    node_file = base_dir / "integrations" / "n8n" / "mne_brain_n8n_node.json"
    node_data = json.loads(node_file.read_text(encoding="utf-8"))
    property_defaults = {
        item["name"]: item.get("default") for item in node_data.get("properties", [])
    }
    if (
        node_data.get("name") == "mneBrainInvestigationTrigger"
        and node_data.get("version") == 2
        and "does not execute" in node_data.get("description", "")
        and property_defaults.get("targetHost") == ""
        and property_defaults.get("alertDescription") == ""
    ):
        print(" [PASS] n8n node contract has no invented target or automatic-execution claim")
        passed += 1
    else:
        errors.append(f"n8n node contract failed: {node_data}")

    print("\n--- MILESTONE 10 VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for error in errors:
            print(f" - {error}")
        return False
    print(f"SUCCESS: {passed} Alert Ingestion Components Verified (0 Errors)")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_milestone_10() else 1)
