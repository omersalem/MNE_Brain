#!/usr/bin/env python3
"""Non-connecting readiness check for the first P2 live read-only pilot."""

import re
import sys
from pathlib import Path
from typing import Any

import yaml


BASE_DIR = Path(__file__).resolve().parent.parent
REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")

sys.path.insert(0, str(BASE_DIR))

from core.entity.build_entity_index import EntityIndexBuilder
from scripts.validate_p0_containment import validate_p0_containment


def _local_env_key_is_set(path: Path, key: str) -> bool:
    """Return only assignment state; never return or print the value."""
    if not path.is_file():
        return False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        candidate, value = line.split("=", 1)
        if candidate.strip() == key:
            return bool(value.strip())
    return False


def run_p2_live_preflight(base_dir: Path = BASE_DIR) -> dict[str, Any]:
    """Evaluate activation prerequisites without resolving secrets or using transport."""
    policy = yaml.safe_load(
        (base_dir / "config" / "p2_readonly_policy.yaml").read_text(encoding="utf-8")
    )
    allowed_profiles = policy.get("allowed_profiles", [])
    profile_name = allowed_profiles[0] if len(allowed_profiles) == 1 else ""
    profile = yaml.safe_load(
        (base_dir / "profiles" / f"{profile_name}.yaml").read_text(encoding="utf-8")
    )
    connection = profile["connection"]
    entity_id = connection["entity_ref"]
    matches = EntityIndexBuilder(base_dir=base_dir).resolve_entity(entity_id)
    exact_target = len(matches) == 1 and matches[0].get("entity_id") == entity_id
    management_ip_present = exact_target and bool(matches[0].get("ip"))

    p0 = validate_p0_containment()
    credential_key = str(connection["credential_ref_env"])
    credential_configured = _local_env_key_is_set(base_dir / ".env", credential_key)
    owner_reference = policy.get("owner_reference")
    owner_authorization = policy.get("owner_authorization")
    target_confirmation = policy.get("target_confirmation_reference")
    adapter_reference = policy.get("live_transport_adapter_reference")

    approved_checks = set(policy.get("allowed_checks", {}).get(profile_name, []))
    declared_checks = {item["id"] for item in profile["read_commands"]}
    scope_exact = (
        allowed_profiles == [profile_name]
        and policy.get("allowed_adapters") == [connection["adapter_id"]]
        and policy.get("allowed_entities") == [entity_id]
        and bool(approved_checks)
        and approved_checks.issubset(declared_checks)
    )

    checks = [
        {
            "check": "p0_containment",
            "ready": p0["success"],
            "blocker": "P0_CONTAINMENT_FAILED",
        },
        {
            "check": "exact_repository_scope",
            "ready": scope_exact,
            "blocker": "P2_SCOPE_MISMATCH",
        },
        {
            "check": "canonical_management_target",
            "ready": management_ip_present,
            "blocker": "CANONICAL_TARGET_MISSING",
        },
        {
            "check": "target_confirmation",
            "ready": bool(
                target_confirmation
                and REFERENCE.fullmatch(str(target_confirmation))
            ),
            "blocker": "TARGET_CONFIRMATION_MISSING",
        },
        {
            "check": "local_credential_configuration",
            "ready": credential_configured,
            "blocker": "LOCAL_CREDENTIAL_NOT_CONFIGURED",
        },
        {
            "check": "sole_owner_proceed",
            "ready": (
                owner_reference == "MNE-BRAIN-OWNER"
                and owner_authorization == "EXPLICIT_OWNER_PROCEED"
            ),
            "blocker": "OWNER_PROCEED_MISSING",
        },
        {
            "check": "live_transport_adapter",
            "ready": bool(
                adapter_reference and REFERENCE.fullmatch(str(adapter_reference))
            ),
            "blocker": "LIVE_TRANSPORT_ADAPTER_MISSING",
        },
        {
            "check": "live_policy_activation",
            "ready": (
                policy.get("enabled") is True
                and policy.get("activation_state") == "OWNER_AUTHORIZED_LIVE_PILOT"
            ),
            "blocker": "LIVE_POLICY_DISABLED",
        },
    ]
    blockers = [item["blocker"] for item in checks if not item["ready"]]
    return {
        "status": "READY" if not blockers else "BLOCKED",
        "mode": "NON_CONNECTING_PREFLIGHT",
        "profile_name": profile_name,
        "target_entity": entity_id,
        "target_resolved": management_ip_present,
        "credential_key": credential_key,
        "credential_value_returned": False,
        "connection_attempted": False,
        "checks_ready": sum(1 for item in checks if item["ready"]),
        "checks_total": len(checks),
        "blockers": blockers,
        "checks": checks,
    }


if __name__ == "__main__":
    report = run_p2_live_preflight()
    print("=" * 68)
    print(" MNE_Brain P2 - Live Pilot Preflight (Non-Connecting)")
    print("=" * 68)
    for item in report["checks"]:
        outcome = "READY" if item["ready"] else f"BLOCKED: {item['blocker']}"
        print(f"[{outcome}] {item['check']}")
    print("=" * 68)
    print(f" PREFLIGHT: {report['status']} | {report['checks_ready']} / {report['checks_total']} READY")
    print(" Credential value returned: no | Connection attempted: no")
    print("=" * 68)
    sys.exit(0 if report["status"] == "READY" else 2)
