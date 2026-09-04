#!/usr/bin/env python3
"""Run the permanent P7 bindings as one owner-authorized read-only baseline."""

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.transports.credentials import CredentialResolver
from core.transports.registry import TransportRegistry
from core.transports.specialized import FMCRestTransport, KerberosPowerShellTransport, VCenterRestTransport
from core.tools.drivers.p7_live import SnmpReadOnlyTransport, VerifiedHTTPTransport


class AuthenticatedBaselineRunner:
    """Thin deterministic collector; it contains no diagnosis or remediation logic."""

    def __init__(self, base_dir: Path = BASE_DIR):
        self.base_dir = Path(base_dir).resolve()
        self.registry = TransportRegistry(base_dir=self.base_dir)
        self.credentials = CredentialResolver(self.base_dir)
        self.plink = Path(self.credentials.local.get("MNE_PLINK_PATH", r"C:\Program Files\PuTTY\plink.exe"))

    @staticmethod
    def _fortigate_blocks(output: str) -> list[tuple[str, dict[str, list[str]]]]:
        blocks: list[tuple[str, dict[str, list[str]]]] = []
        current_id = ""
        current: dict[str, list[str]] = {}
        for raw_line in output.splitlines():
            line = raw_line.strip()
            edit = re.fullmatch(r"edit\s+(.+)", line, re.I)
            if edit:
                current_id = edit.group(1).strip().strip('"')[:160]
                current = {}
                continue
            if line.casefold() == "next" and current_id:
                blocks.append((current_id, current))
                current_id, current = "", {}
                continue
            setting = re.fullmatch(r"set\s+([a-z0-9_-]+)\s+(.+)", line, re.I)
            if setting and current_id:
                try:
                    values = shlex.split(setting.group(2), posix=True)
                except ValueError:
                    values = [setting.group(2).strip().strip('"')]
                current[setting.group(1).casefold()] = [str(item)[:300] for item in values[:80]]
        return blocks

    @classmethod
    def _normalized_facts(cls, check_id: str, output: str) -> list[dict[str, Any]]:
        if check_id == "firewall_addresses":
            facts = []
            for name, values in cls._fortigate_blocks(output):
                fact = {"object_name": name}
                for field in ("subnet", "type", "fqdn", "start-ip", "end-ip", "associated-interface"):
                    if field in values:
                        fact[field.replace("-", "_")] = values[field]
                if len(fact) > 1:
                    facts.append(fact)
            return facts[:2000]
        if check_id == "firewall_policies":
            facts = []
            allowed = ("name", "srcintf", "dstintf", "srcaddr", "dstaddr", "action", "schedule", "service", "nat", "status")
            for policy_id, values in cls._fortigate_blocks(output):
                fact: dict[str, Any] = {"policy_id": policy_id}
                for field in allowed:
                    if field in values:
                        fact[field] = values[field]
                facts.append(fact)
            return facts[:2000]
        if check_id == "system_status":
            facts = []
            for line in output.splitlines():
                if ":" in line and len(facts) < 30:
                    key, value = line.split(":", 1)
                    if re.fullmatch(r"[A-Za-z][A-Za-z0-9 _/-]{1,60}", key.strip()):
                        facts.append({"field": key.strip(), "value": value.strip()[:500]})
            return facts
        return []

    @classmethod
    def _result(cls, binding_id: str, status: str, *, attempted: bool = False, output: str = "", check_id: str = "") -> dict[str, Any]:
        encoded = output.encode("utf-8", "replace")
        return {
            "binding_id": binding_id,
            "status": status,
            "connection_attempted": attempted,
            "output_bytes": len(encoded),
            "output_sha256_prefix": hashlib.sha256(encoded).hexdigest()[:16] if encoded else "",
            "normalized_facts": cls._normalized_facts(check_id, output) if status == "SUCCESS" else [],
            "raw_output_included": False,
            "credential_returned": False,
            "persistence_attempted": False,
            "remediation_attempted": False,
        }

    @staticmethod
    def _credential_prefix(binding: dict[str, Any]) -> str:
        """Keep a device identity namespace separate from its read-only credential scope."""
        return str(binding.get("credential_env_prefix") or binding["env_prefix"])

    def _ssh(self, binding: dict[str, Any], *, allow_interactive_fallback: bool = True) -> dict[str, Any]:
        identity_prefix, binding_id = binding["env_prefix"], binding["binding_id"]
        credential_prefix = self._credential_prefix(binding)
        configured_host = self.credentials.value(f"{identity_prefix}_HOST")
        host = configured_host or str(binding.get("target", ""))
        pin = self.credentials.value(f"{identity_prefix}_SSH_HOSTKEY")
        if not host or not pin:
            return self._result(binding_id, "TARGET_OR_IDENTITY_NOT_CONFIGURED", check_id=binding["check_id"])
        try:
            if configured_host and configured_host != host:
                raise ValueError("Configured target differs from the binding target.")
            username, password = self.credentials.resolve_pair(
                username_key=f"{credential_prefix}_USERNAME", password_key=f"{credential_prefix}_PASSWORD"
            )
        except ValueError:
            return self._result(binding_id, "CREDENTIAL_NOT_CONFIGURED", check_id=binding["check_id"])
        if not self.plink.is_file():
            return self._result(binding_id, "TRANSPORT_DEPENDENCY_MISSING", check_id=binding["check_id"])
        base = [str(self.plink), "-batch", "-no-antispoof", "-ssh", "-P", "22", "-hostkey", pin,
                "-l", username, "-pwfile"]
        output, completed = "", None
        with TemporaryDirectory(prefix="mne-p7-baseline-") as directory:
            password_file = Path(directory) / "credential.txt"
            password_file.write_text(password + "\n", encoding="utf-8")
            try:
                password_file.chmod(0o600)
            except OSError:
                pass
            arguments = base + [str(password_file), host]
            try:
                completed = subprocess.run(
                    arguments + [binding["operation"]], check=False, capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=18,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                output = completed.stdout or ""
            except subprocess.TimeoutExpired:
                completed = None
            if allow_interactive_fallback and (completed is None or completed.returncode != 0 or not output.strip()):
                try:
                    interactive_input = binding["operation"] + "\nexit\n"
                    if binding["platform"] == "zyxel_switch":
                        interactive_input = "show version\nshow system-information\nexit\n"
                    completed = subprocess.run(
                        arguments, input=interactive_input, check=False,
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
                    output = completed.stdout or ""
                except subprocess.TimeoutExpired:
                    return self._result(binding_id, "TIMEOUT", attempted=True, check_id=binding["check_id"])
        if completed is None:
            return self._result(binding_id, "TRANSPORT_FAILED", attempted=True, check_id=binding["check_id"])
        error = (completed.stderr or "").casefold()
        lowered = output.casefold()
        if completed.returncode != 0 and ("access denied" in error or "authentication" in error):
            return self._result(binding_id, "AUTHENTICATION_FAILED", attempted=True, check_id=binding["check_id"])
        if completed.returncode != 0:
            return self._result(binding_id, "TRANSPORT_FAILED", attempted=True, check_id=binding["check_id"])
        if not output.strip():
            return self._result(binding_id, "EMPTY_OUTPUT", attempted=True, check_id=binding["check_id"])
        if any(marker in lowered for marker in ("unknown command", "invalid input", "command not found", "unrecognized command")) and len(output) < 300:
            return self._result(binding_id, "COMMAND_REJECTED", attempted=True, output=output, check_id=binding["check_id"])
        if binding["platform"] == "fortinet_fortios" and binding["check_id"] == "system_status" and "version:" not in lowered:
            return self._result(binding_id, "IDENTITY_NOT_CONFIRMED", attempted=True, output=output, check_id=binding["check_id"])
        return self._result(binding_id, "SUCCESS", attempted=True, output=output, check_id=binding["check_id"])

    def _winrm(self, binding: dict[str, Any]) -> dict[str, Any]:
        result = KerberosPowerShellTransport(self.base_dir, timeout=30).collect(
            prefix=self._credential_prefix(binding), target=binding["kerberos_fqdn"], operation=binding["operation"]
        )
        return self._result(binding["binding_id"], str(result["status"]), attempted=bool(result.get("connection_attempted")), output=str(result.get("output") or ""), check_id=binding["check_id"])

    def _powershell(self, binding: dict[str, Any]) -> dict[str, Any]:
        result = KerberosPowerShellTransport(self.base_dir, timeout=30).collect(
            prefix=self._credential_prefix(binding), target=binding["kerberos_fqdn"], operation=binding["operation"],
            exchange_endpoint=binding.get("endpoint_path", ""),
        )
        return self._result(binding["binding_id"], str(result["status"]), attempted=bool(result.get("connection_attempted")), output=str(result.get("output") or ""), check_id=binding["check_id"])

    def _rest(self, binding: dict[str, Any]) -> dict[str, Any]:
        if binding["platform"] == "vmware_vcenter":
            result = VCenterRestTransport(self.base_dir, timeout=20).collect(binding["operation"])
        elif binding["platform"] == "cisco_fmc":
            result = FMCRestTransport(self.base_dir, timeout=20).collect(binding["operation"])
        else:
            identity_prefix = binding["env_prefix"]
            credential_prefix = self._credential_prefix(binding)
            target = self.credentials.value(f"{identity_prefix}_HOST") or str(binding.get("target", ""))
            pin = self.credentials.value(f"{identity_prefix}_TLS_CERT_SHA256")
            if not target or not pin:
                result = {"status": "TARGET_OR_IDENTITY_NOT_CONFIGURED", "connection_attempted": False, "output": ""}
            else:
                try:
                    username, password = self.credentials.resolve_pair(
                        username_key=f"{credential_prefix}_USERNAME", password_key=f"{credential_prefix}_PASSWORD"
                    )
                except ValueError:
                    result = {"status": "CREDENTIAL_NOT_CONFIGURED", "connection_attempted": False, "output": ""}
                else:
                    method, path = binding["operation"].split(" ", 1)
                    result = VerifiedHTTPTransport(target=target, certificate_sha256=pin, timeout_seconds=20).request(
                        method, path, username=username, password=password
                    )
        return self._result(binding["binding_id"], str(result["status"]), attempted=bool(result.get("connection_attempted")), output=str(result.get("output") or ""), check_id=binding["check_id"])

    def _snmp(self, binding: dict[str, Any]) -> dict[str, Any]:
        prefix = binding["env_prefix"]
        engine_id = self.credentials.value(f"{prefix}_SNMP_ENGINE_ID") or self.credentials.value("SNMPV3_ENGINE_ID")
        credential_ref = self.credentials.value(str(binding.get("credential_ref_env", "")))
        readiness = SnmpReadOnlyTransport().readiness(engine_id=engine_id, credential_reference=credential_ref)
        return self._result(binding["binding_id"], str(readiness["status"]), attempted=False, check_id=binding["check_id"])

    def _execute(self, binding: dict[str, Any], *, single_attempt: bool = False) -> dict[str, Any]:
        if binding["protocol"] == "ssh":
            return self._ssh(binding, allow_interactive_fallback=not single_attempt)
        return {"winrm": self._winrm, "powershell": self._powershell, "rest": self._rest, "snmp": self._snmp}[binding["protocol"]](binding)

    def run_selected(self, *, owner_proceed: bool, binding_ids: list[str], maximum_workers: int = 3) -> dict[str, Any]:
        requested = list(dict.fromkeys(binding_ids))
        active_by_id = {item["binding_id"]: item for item in self.registry.binding_catalog["bindings"] if item["scope_status"] == "ACTIVE"}
        if not requested or len(requested) > 3 or any(item not in active_by_id for item in requested):
            return {"status": "NOT_RUN", "reason": "EXACT_ACTIVE_SCOPE_REQUIRED", "total_bindings": 0, "results": []}
        active = [active_by_id[item] for item in requested]
        if not owner_proceed:
            return {"status": "NOT_RUN", "reason": "OWNER_PROCEED_REQUIRED", "total_bindings": len(active), "results": []}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(maximum_workers, 8))) as executor:
            results = list(executor.map(self._execute, active))
        counts: dict[str, int] = {}
        for item in results:
            counts[item["status"]] = counts.get(item["status"], 0) + 1
        return {
            "status": "COMPLETE",
            "owner_reference": "MNE-BRAIN-OWNER",
            "total_bindings": len(active),
            "status_counts": counts,
            "results": results,
            "owner_excluded_bindings": 1,
            "raw_output_included": False,
            "credentials_returned": False,
            "persistence_attempted": False,
            "notifications_sent": False,
            "remediation_attempted": False,
        }

    def run_exact(self, *, owner_proceed: bool, binding_id: str, target: str, check_id: str) -> dict[str, Any]:
        """Run one exact owner-approved scope after binding, target, and check revalidation."""
        active_by_id = {
            item["binding_id"]: item
            for item in self.registry.binding_catalog["bindings"]
            if item["scope_status"] == "ACTIVE"
        }
        binding = active_by_id.get(binding_id)
        if not binding or not target or binding.get("check_id") != check_id:
            return {"status": "NOT_RUN", "reason": "EXACT_ACTIVE_SCOPE_REQUIRED", "total_bindings": 0, "results": []}
        if not owner_proceed:
            return {"status": "NOT_RUN", "reason": "OWNER_PROCEED_REQUIRED", "total_bindings": 1, "results": []}
        configured_target = (
            str(binding.get("kerberos_fqdn", ""))
            if binding["protocol"] in {"winrm", "powershell"}
            else (self.credentials.value(f"{binding['env_prefix']}_HOST") or str(binding.get("target", "")))
        )
        if configured_target != target:
            return {"status": "NOT_RUN", "reason": "EXACT_TARGET_NOT_CONFIGURED", "total_bindings": 1, "results": []}
        result = self._execute(binding, single_attempt=True)
        return {
            "status": "COMPLETE",
            "owner_reference": "MNE-BRAIN-OWNER",
            "total_bindings": 1,
            "status_counts": {result["status"]: 1},
            "results": [result],
            "raw_output_included": False,
            "credentials_returned": False,
            "persistence_attempted": False,
            "notifications_sent": False,
            "remediation_attempted": False,
        }

    def run(self, *, owner_proceed: bool, maximum_workers: int = 8) -> dict[str, Any]:
        active = [item["binding_id"] for item in self.registry.binding_catalog["bindings"] if item["scope_status"] == "ACTIVE"]
        # The full P7 baseline is the sole exception to the P8 three-binding troubleshooting cap.
        if not owner_proceed:
            return {"status": "NOT_RUN", "reason": "OWNER_PROCEED_REQUIRED", "total_bindings": len(active), "results": []}
        selected = [item for item in self.registry.binding_catalog["bindings"] if item["binding_id"] in active]
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(maximum_workers, 8))) as executor:
            results = list(executor.map(self._execute, selected))
        counts: dict[str, int] = {}
        for item in results:
            counts[item["status"]] = counts.get(item["status"], 0) + 1
        return {"status": "COMPLETE", "owner_reference": "MNE-BRAIN-OWNER", "total_bindings": len(selected), "status_counts": counts, "results": results, "owner_excluded_bindings": 1, "raw_output_included": False, "credentials_returned": False, "persistence_attempted": False, "notifications_sent": False, "remediation_attempted": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-proceed", action="store_true")
    args = parser.parse_args()
    result = AuthenticatedBaselineRunner().run(owner_proceed=args.owner_proceed)
    print(json.dumps({key: value for key, value in result.items() if key != "results"}, indent=2))
    raise SystemExit(0 if result["status"] == "COMPLETE" and result.get("status_counts", {}).get("SUCCESS") == result["total_bindings"] else 1)
