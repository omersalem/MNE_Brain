"""Bounded unauthenticated reachability preflight for all canonical entities."""

import socket
from pathlib import Path
from typing import Callable

from core.transports.registry import TransportRegistry


Probe = Callable[[str, int, float], bool]


class LivePreflightValidator:
    """Validate reachability without credentials, commands, persistence, or trust promotion."""

    PORTS = {"ssh": 22, "rest": 443, "powershell": 5985, "winrm": 5985, "vmware": 443, "snmp": 161}

    def __init__(self, base_dir: Path | None = None, *, probe: Probe | None = None):
        self.registry = TransportRegistry(base_dir=base_dir)
        self.probe = probe or self._tcp_probe

    @staticmethod
    def _tcp_probe(target: str, port: int, timeout: float) -> bool:
        try:
            with socket.create_connection((target, port), timeout=timeout):
                return True
        except OSError:
            return False

    def validate_entity(self, entity_id: str, *, owner_proceed: bool, timeout_seconds: float = 2.0) -> dict:
        plan = self.registry.target_plan(entity_id)
        if not owner_proceed:
            return self._blocked(entity_id, "OWNER_PROCEED_REQUIRED")
        if plan.get("status") != "PLANNED_READ_ONLY":
            return self._blocked(entity_id, "INVALID_EXACT_TARGET")
        protocol = str(plan["protocol"])
        port = self.PORTS[protocol]
        if protocol == "snmp":
            return {
                **self._blocked(entity_id, "SNMP_IDENTITY_AND_CREDENTIAL_NOT_CONFIGURED"),
                "target_disposition": plan["target_disposition"],
                "transport": protocol,
                "port": port,
            }
        reachable = self.probe(str(plan["candidate_target"]), port, min(max(timeout_seconds, 0.1), 15.0))
        if not reachable:
            status = "TARGET_UNREACHABLE"
        elif plan["identity_proof_required"]:
            status = "LIVE_REACHABLE_IDENTITY_PROOF_REQUIRED"
        else:
            status = "LIVE_REACHABLE_UNAUTHENTICATED"
        return {
            "status": status,
            "entity_id": entity_id,
            "transport": protocol,
            "port": port,
            "target_disposition": plan["target_disposition"],
            "connection_attempted": True,
            "authenticated": False,
            "trust_level": 0,
            "evidence_accepted": False,
            "persistence_attempted": False,
            "remediation_attempted": False,
        }

    def validate_all(self, *, owner_proceed: bool, timeout_seconds: float = 2.0) -> dict:
        results = [self.validate_entity(entity_id, owner_proceed=owner_proceed, timeout_seconds=timeout_seconds) for entity_id in sorted(self.registry.entities)]
        counts: dict[str, int] = {}
        for item in results:
            counts[item["status"]] = counts.get(item["status"], 0) + 1
        return {
            "status": "COMPLETE" if owner_proceed else "NOT_RUN",
            "owner_reference": "MNE-BRAIN-OWNER",
            "total_entities": len(results),
            "status_counts": counts,
            "results": results,
            "raw_output_included": False,
            "credentials_returned": False,
            "persistence_attempted": False,
            "notifications_sent": False,
            "remediation_attempted": False,
        }

    @staticmethod
    def _blocked(entity_id: str, reason: str) -> dict:
        return {"status": reason, "entity_id": entity_id, "connection_attempted": False, "authenticated": False, "trust_level": 0, "evidence_accepted": False, "persistence_attempted": False, "remediation_attempted": False}
