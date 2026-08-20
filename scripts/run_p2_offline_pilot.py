#!/usr/bin/env python3
"""Run P2 read-only operationalization scenarios with non-connecting fixtures."""

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
from threading import Event
from typing import Any, Callable

import yaml

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.entity.build_entity_index import EntityIndexBuilder
from core.evidence.build_evidence_pack import EvidencePackBuilder
from core.llm.llm_adapter import LLMAdapter
from core.reasoning.investigation_planner import InvestigationPlanner
from core.router.route_query import QueryRouter
from core.verification.live_verify import LiveVerificationEngine
from core.verification.readonly_adapter import ReadOnlyVerificationAdapter


def _build_fixture_workspace(root: Path) -> None:
    copytree(base_dir / "00_meta" / "schemas", root / "00_meta" / "schemas")
    copytree(base_dir / "profiles", root / "profiles")
    copytree(base_dir / "knowledge", root / "knowledge")
    (root / "config").mkdir(parents=True)
    policy = yaml.safe_load(
        (base_dir / "config" / "p2_readonly_policy.yaml").read_text(encoding="utf-8")
    )
    policy["enabled"] = True
    policy["activation_state"] = "OFFLINE_FIXTURE_ONLY"
    policy["reason"] = "Temporary isolated fixture policy; no live transport is present."
    policy["allowed_checks"]["fortigate_edge"] = ["system_status", "interface_stats"]
    policy["maximum_checks_per_request"] = 2
    (root / "config" / "p2_readonly_policy.yaml").write_text(
        yaml.safe_dump(policy, sort_keys=False), encoding="utf-8"
    )


def _engine(
    root: Path, callback: Callable[[dict[str, Any]], dict[str, Any]]
) -> LiveVerificationEngine:
    adapter = ReadOnlyVerificationAdapter(
        "fortigate_ssh_readonly",
        callback,
        simulation_mode=True,
        base_dir=root,
    )
    return LiveVerificationEngine(
        base_dir=root,
        adapters={"fortigate_ssh_readonly": adapter},
    )


def _execute(
    root: Path,
    callback: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    check_id: str = "system_status",
    authorized: bool = True,
    entity_id: str = "fw-fortigate-edge-01",
    cancellation_event: Event | None = None,
) -> dict[str, Any]:
    return _engine(root, callback).execute_live_verification(
        "fortigate_edge",
        check_id=check_id,
        authorized=authorized,
        entity_id=entity_id,
        scope_reference="p2-offline-fixture-01",
        credential_reference="secretref://offline/fortigate-readonly",
        cancellation_event=cancellation_event,
    )


def run_p2_offline_pilot() -> dict[str, Any]:
    print("=" * 72)
    print(" MNE_Brain P2 - Offline Read-Only Operationalization Pilot")
    print("=" * 72)
    results: list[dict[str, Any]] = []

    def scenario(scenario_id: str, name: str, check: Callable[[], tuple[bool, str]]) -> None:
        started = time.perf_counter()
        try:
            passed, detail = check()
        except Exception as exc:
            passed, detail = False, f"{type(exc).__name__}: {exc}"
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        results.append(
            {
                "id": scenario_id,
                "name": name,
                "passed": bool(passed),
                "detail": detail,
                "duration_ms": duration_ms,
            }
        )
        print(f"[{'PASS' if passed else 'FAIL'}] {scenario_id} {name} | {duration_ms:.3f} ms | {detail}")

    with TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        _build_fixture_workspace(root)

        def system_fixture(_request: dict[str, Any]) -> dict[str, Any]:
            return {
                "status": "SIMULATED_SUCCESS",
                "connection_attempted": False,
                "output": "Hostname: offline-fw\nVersion: fixture-only\npassword=fixture-secret",
            }

        def interface_fixture(_request: dict[str, Any]) -> dict[str, Any]:
            return {
                "status": "SIMULATED_SUCCESS",
                "connection_attempted": False,
                "output": "Interface port2 status down; link down; token=fixture-token",
            }

        def simulation_boundary() -> tuple[bool, str]:
            verification = _execute(root, system_fixture)
            targets = EntityIndexBuilder(base_dir=root).resolve_entity("fw-fortigate-edge-01")
            pack = EvidencePackBuilder(base_dir=root).build_evidence_pack(
                "Check fw-fortigate-edge-01 status",
                targets,
                supplemental_evidence=verification["telemetry_results"],
            )
            answer = LLMAdapter(base_dir=base_dir).generate_response("Check firewall status", pack)
            serialized = str(verification)
            passed = (
                verification["status"] == "SIMULATED_NOT_ACCEPTED"
                and verification["trust_level"] == 0
                and verification["connection_attempted"] is False
                and pack["evidence_blocks"] == []
                and answer["evidence_status"] == "INSUFFICIENT_EVIDENCE"
                and "fixture-secret" not in serialized
            )
            return passed, "fixture output remains trust 0 and cannot enter the evidence pack"

        scenario("p2-01", "simulation trust boundary", simulation_boundary)

        def reasoning_boundary() -> tuple[bool, str]:
            verification = _execute(root, interface_fixture, check_id="interface_stats")
            reasoning = InvestigationPlanner().evaluate_investigation_state(
                [], verification["telemetry_results"]
            )
            passed = (
                verification["status"] == "SIMULATED_NOT_ACCEPTED"
                and reasoning["reasoning_status"] == "PENDING_EVIDENCE"
                and reasoning["stop_early_triggered"] is False
                and reasoning["accepted_evidence_refs"] == []
            )
            return passed, "simulated link-down text cannot trigger a root-cause conclusion"

        scenario("p2-02", "simulated incident reasoning", reasoning_boundary)

        def timeout_boundary() -> tuple[bool, str]:
            result = _execute(
                root,
                lambda _request: {
                    "status": "TIMEOUT",
                    "connection_attempted": False,
                    "output": None,
                },
            )
            passed = result["status"] == "SIMULATION_FAILED" and result["failures"] == [
                {"check_id": "system_status", "status": "TIMEOUT"}
            ]
            return passed, "timeout produces no evidence"

        scenario("p2-03", "transport timeout", timeout_boundary)

        def authorization_boundary() -> tuple[bool, str]:
            calls: list[dict[str, Any]] = []
            result = _execute(
                root,
                lambda request: calls.append(request) or {},
                authorized=False,
            )
            return result["status"] == "NOT_RUN" and not calls, "missing authorization never reaches the adapter"

        scenario("p2-04", "missing authorization", authorization_boundary)

        def scope_boundary() -> tuple[bool, str]:
            result = _execute(root, system_fixture, entity_id="fw-fortigate-jenin-01")
            return result["status"] == "SCOPE_BLOCKED", "out-of-scope entity is blocked before collection"

        scenario("p2-05", "entity scope enforcement", scope_boundary)

        def output_budget_boundary() -> tuple[bool, str]:
            result = _execute(
                root,
                lambda _request: {
                    "status": "SIMULATED_SUCCESS",
                    "connection_attempted": False,
                    "output": "x" * 65537,
                },
            )
            return (
                result["status"] == "SIMULATION_FAILED"
                and result["failures"][0]["status"] == "OUTPUT_TOO_LARGE",
                "oversized output is rejected before evidence construction",
            )

        scenario("p2-06", "output-size budget", output_budget_boundary)

        def cancellation_boundary() -> tuple[bool, str]:
            cancellation = Event()
            cancellation.set()
            result = _execute(root, system_fixture, cancellation_event=cancellation)
            return result["status"] == "CANCELLED" and result["checks_attempted"] == 0, "pre-set cancellation prevents collection"

        scenario("p2-07", "cancellation", cancellation_boundary)

        def malformed_boundary() -> tuple[bool, str]:
            result = _execute(root, lambda _request: ["invalid"])  # type: ignore[return-value]
            return (
                result["status"] == "SIMULATION_FAILED"
                and result["failures"][0]["status"] == "INVALID_TRANSPORT_RESULT",
                "malformed transport result produces no evidence",
            )

        scenario("p2-08", "malformed transport result", malformed_boundary)

        def redaction_boundary() -> tuple[bool, str]:
            result = _execute(root, system_fixture)
            record = result["telemetry_results"][0]
            passed = (
                "fixture-secret" not in record["content"]
                and "[REDACTED]" in record["content"]
                and "get system status" not in str(result)
                and "secretref://offline/fortigate-readonly" not in str(result)
                and "command" not in result
                and "credential_reference" not in result
            )
            return passed, "credential-like output, commands, and references are absent"

        scenario("p2-09", "redaction and response minimization", redaction_boundary)

        def expiry_boundary() -> tuple[bool, str]:
            now = datetime.now(timezone.utc)
            expired = {
                "evidence_id": "ev-live-0000000000000000",
                "entity_id": "fw-fortigate-edge-01",
                "source_file": "live-adapter://fortigate_ssh_readonly/system_status",
                "source": "owner-authorized read-only transport",
                "evidence_status": "live_verified",
                "trust_level": 5,
                "observed_at": (now - timedelta(hours=2)).isoformat(),
                "expires_at": (now - timedelta(hours=1)).isoformat(),
                "evidence_refs": ["ev-live-0000000000000000"],
                "verification_target": "fw-fortigate-edge-01",
                "verification_check_id": "system_status",
                "verification_outcome": "success",
                "content": "Expired fixture content",
            }
            targets = EntityIndexBuilder(base_dir=root).resolve_entity("fw-fortigate-edge-01")
            pack = EvidencePackBuilder(base_dir=root).build_evidence_pack(
                "Check firewall status", targets, supplemental_evidence=[expired]
            )
            return pack["evidence_blocks"] == [] and any("expired" in item for item in pack["unknowns"]), "expired evidence is rejected"

        scenario("p2-10", "freshness enforcement", expiry_boundary)

        def clarification_boundary() -> tuple[bool, str]:
            route = QueryRouter(base_dir=root).classify_query("Unknown mystery outage")
            passed = (
                route["resolution_status"] == "unknown"
                and route["clarification_request"]["requires_clarification"] is True
            )
            return passed, "unknown incident requests a target instead of guessing"

        scenario("p2-11", "unknown-target clarification", clarification_boundary)

    passed_count = sum(result["passed"] for result in results)
    report = {
        "success": passed_count == len(results) == 11,
        "mode": "OFFLINE_FIXTURE_ONLY",
        "passed": passed_count,
        "total": len(results),
        "maximum_duration_ms": max(result["duration_ms"] for result in results),
        "live_connections_attempted": 0,
        "accepted_live_evidence": 0,
        "results": results,
    }
    print("=" * 72)
    print(f" P2 OFFLINE PILOT: {passed_count} / {len(results)} SCENARIOS PASSED")
    print(" Accepted live evidence: 0 | Live connections attempted: 0")
    print("=" * 72)
    return report


if __name__ == "__main__":
    sys.exit(0 if run_p2_offline_pilot()["success"] else 1)
