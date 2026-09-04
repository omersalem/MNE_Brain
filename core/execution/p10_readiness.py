"""Safe, non-secret P10 platform and binding readiness inventory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from core.execution.p10_catalog import P10OperationCatalog
from core.execution.p10_commands import P10CommandError, render_wire
from core.transports.credentials import CredentialResolver
from core.infrastructure.coverage import InfrastructureCoverageService


PLATFORM_COMPATIBILITY = {
    "windows_powershell": {"windows_identity", "microsoft_exchange"},
    "cisco_switching": {"cisco_iosxe", "cisco_router"},
    "fujitsu_switching": {"fujitsu_switch"},
    "linux_host": {"linux_host"},
    "vmware_vcenter": {"vmware_vcenter"},
    "fortinet_fortios": {"fortinet_fortios"},
    "f5_bigip": {"f5_bigip"},
    "cisco_fmc": {"cisco_fmc"},
}


class P10ReadinessService:
    """Report code, target, identity, credential, and authorization dimensions."""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir).resolve()
        self.credentials = CredentialResolver(self.base_dir)
        self.catalog = P10OperationCatalog(self.base_dir)
        self.bindings = (yaml.safe_load((self.base_dir / "config/p7_device_bindings.yaml").read_text(encoding="utf-8")) or {}).get("bindings", [])
        self.registry = (yaml.safe_load((self.base_dir / "config/p10_platform_registry.yaml").read_text(encoding="utf-8")) or {}).get("platforms", {})
        self.coverage = InfrastructureCoverageService(self.base_dir)

    def _target(self, binding: dict[str, Any]) -> str:
        return str(binding.get("kerberos_fqdn") or self.credentials.value(f"{binding['env_prefix']}_HOST") or binding.get("target", ""))

    def _identity(self, binding: dict[str, Any]) -> tuple[str, bool]:
        prefix = binding["env_prefix"]
        if binding.get("identity_mode") == "KERBEROS_FQDN":
            return f"{binding.get('kerberos_fqdn', '')} (Kerberos SPN)", bool(binding.get("kerberos_fqdn"))
        key = f"{prefix}_TLS_CERT_SHA256" if binding.get("identity_mode") == "PINNED_TLS_CERT" else f"{prefix}_SSH_HOSTKEY"
        return key, bool(self.credentials.value(key))

    def _write_credentials(self, prefix: str) -> tuple[str, bool]:
        reference_key = f"{prefix}_WRITE_CREDENTIAL_REF"
        reference = self.credentials.value(reference_key)
        configured = bool(reference.startswith("secretref://") and self.credentials.value(f"{prefix}_WRITE_USERNAME") and self.credentials.value(f"{prefix}_WRITE_PASSWORD"))
        return reference_key, configured

    def _renderer_coverage(self, platform: str) -> dict[str, Any]:
        forward: list[str] = []
        rollback: list[str] = []
        blocked: list[str] = []
        for operation in self.catalog._operations.values():
            if operation["platform"] != platform:
                continue
            for action in operation["action_variants"]:
                transaction = {
                    "platform": platform,
                    "operation_type": operation["operation_type"],
                    "action": action,
                    "arguments": {"resource_name": "SAFE_OBJECT", "value": "192.0.2.10", "secondary_value": "SAFE_SECONDARY", "interface": "GigabitEthernet1/0/1"},
                    "rollback": False,
                }
                label = f"{operation['operation_id']}:{action}"
                try:
                    render_wire(transaction); forward.append(label)
                except P10CommandError:
                    blocked.append(label); continue
                transaction["rollback"] = True
                try:
                    render_wire(transaction); rollback.append(label)
                except P10CommandError:
                    pass
        return {"forward_supported": forward, "rollback_supported": rollback, "blocked_actions": blocked}

    def status(self) -> dict[str, Any]:
        platforms = []
        for platform, settings in self.registry.items():
            bindings = []
            for binding in self.bindings:
                if binding.get("platform") not in PLATFORM_COMPATIBILITY[platform]:
                    continue
                target = self._target(binding)
                identity_ref, identity_ok = self._identity(binding)
                credential_ref, credential_ok = self._write_credentials(binding["env_prefix"])
                blockers = []
                if binding.get("scope_status") != "ACTIVE": blockers.append("P7_BINDING_NOT_ACTIVE")
                if not target: blockers.append("EXACT_TARGET_NOT_CONFIGURED")
                if not identity_ok: blockers.append("IDENTITY_PIN_NOT_CONFIGURED")
                if not credential_ok: blockers.append("SEPARATE_WRITE_CREDENTIAL_NOT_CONFIGURED")
                if credential_ok: blockers.append("SAFE_WRITE_AUTHORIZATION_PROBE_REQUIRED")
                bindings.append({
                    "binding_id": binding["binding_id"], "target": target or "NOT_CONFIGURED", "protocol": binding["protocol"],
                    "identity_reference": identity_ref, "identity_configured": identity_ok,
                    "write_credential_reference": credential_ref, "write_credentials_configured": credential_ok,
                    "write_authorization": "NOT_CHECKED" if credential_ok else "NOT_CONFIGURED",
                    "live_write_ready": False, "blockers": blockers,
                })
            coverage = self._renderer_coverage(platform)
            platforms.append({
                "platform": platform, "transport": settings["transport"], "driver_implemented": True,
                "global_write_enabled": False, "live_write_ready": False,
                "precheck": settings["precheck"], "postcheck": settings["postcheck"], "abort": settings["abort"],
                "bindings": bindings, "renderer_coverage": coverage,
            })
        return {
            "phase": "P10", "status": "BLOCKED_BEFORE_FIRST_REAL_WRITE", "global_write_enabled": False,
            "mode": "OWNER_FULL_CONTROL", "automatic_read_only_discovery_allowed": True,
            "approval_required_before_every_write": True, "one_approval_covers_displayed_rollback": True,
            "rollback_requires_separate_approval": False, "platforms": platforms,
            "asset_coverage": self.coverage.status(),
        }
