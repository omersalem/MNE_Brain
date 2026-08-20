#!/usr/bin/env python3
"""Run the permanent P7 bindings as one owner-authorized read-only baseline."""

import argparse
import concurrent.futures
import hashlib
import json
import os
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


class AuthenticatedBaselineRunner:
    """Thin deterministic collector; it contains no diagnosis or remediation logic."""

    def __init__(self, base_dir: Path = BASE_DIR):
        self.base_dir = Path(base_dir).resolve()
        self.registry = TransportRegistry(base_dir=self.base_dir)
        self.credentials = CredentialResolver(self.base_dir)
        self.plink = Path(self.credentials.local.get("MNE_PLINK_PATH", r"C:\Program Files\PuTTY\plink.exe"))

    @staticmethod
    def _result(binding_id: str, status: str, *, attempted: bool = False, output: str = "") -> dict[str, Any]:
        encoded = output.encode("utf-8", "replace")
        return {
            "binding_id": binding_id,
            "status": status,
            "connection_attempted": attempted,
            "output_bytes": len(encoded),
            "output_sha256_prefix": hashlib.sha256(encoded).hexdigest()[:16] if encoded else "",
            "raw_output_included": False,
            "credential_returned": False,
            "persistence_attempted": False,
            "remediation_attempted": False,
        }

    def _ssh(self, binding: dict[str, Any]) -> dict[str, Any]:
        prefix, binding_id = binding["env_prefix"], binding["binding_id"]
        host = self.credentials.value(f"{prefix}_HOST")
        pin = self.credentials.value(f"{prefix}_SSH_HOSTKEY")
        if not host or not pin:
            return self._result(binding_id, "TARGET_OR_IDENTITY_NOT_CONFIGURED")
        try:
            username, password = self.credentials.resolve(
                target=host,
                host_key=f"{prefix}_HOST",
                username_key=f"{prefix}_USERNAME",
                password_key=f"{prefix}_PASSWORD",
            )
        except ValueError:
            return self._result(binding_id, "CREDENTIAL_NOT_CONFIGURED")
        if not self.plink.is_file():
            return self._result(binding_id, "TRANSPORT_DEPENDENCY_MISSING")
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
            if completed is None or completed.returncode != 0 or not output.strip():
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
                    return self._result(binding_id, "TIMEOUT", attempted=True)
        if completed is None:
            return self._result(binding_id, "TRANSPORT_FAILED", attempted=True)
        error = (completed.stderr or "").casefold()
        lowered = output.casefold()
        if completed.returncode != 0 and ("access denied" in error or "authentication" in error):
            return self._result(binding_id, "AUTHENTICATION_FAILED", attempted=True)
        if completed.returncode != 0:
            return self._result(binding_id, "TRANSPORT_FAILED", attempted=True)
        if not output.strip():
            return self._result(binding_id, "EMPTY_OUTPUT", attempted=True)
        if any(marker in lowered for marker in ("unknown command", "invalid input", "command not found", "unrecognized command")) and len(output) < 300:
            return self._result(binding_id, "COMMAND_REJECTED", attempted=True, output=output)
        if binding["platform"] == "fortinet_fortios" and "version:" not in lowered:
            return self._result(binding_id, "IDENTITY_NOT_CONFIRMED", attempted=True, output=output)
        return self._result(binding_id, "SUCCESS", attempted=True, output=output)

    def _winrm(self, binding: dict[str, Any]) -> dict[str, Any]:
        result = KerberosPowerShellTransport(self.base_dir, timeout=30).collect(
            prefix=binding["env_prefix"], target=binding["kerberos_fqdn"], operation=binding["operation"]
        )
        return self._result(binding["binding_id"], str(result["status"]), attempted=bool(result.get("connection_attempted")), output=str(result.get("output") or ""))

    def _powershell(self, binding: dict[str, Any]) -> dict[str, Any]:
        result = KerberosPowerShellTransport(self.base_dir, timeout=30).collect(
            prefix=binding["env_prefix"], target=binding["kerberos_fqdn"], operation=binding["operation"],
            exchange_endpoint=binding.get("endpoint_path", ""),
        )
        return self._result(binding["binding_id"], str(result["status"]), attempted=bool(result.get("connection_attempted")), output=str(result.get("output") or ""))

    def _rest(self, binding: dict[str, Any]) -> dict[str, Any]:
        transport = VCenterRestTransport(self.base_dir, timeout=20) if binding["platform"] == "vmware_vcenter" else FMCRestTransport(self.base_dir, timeout=20)
        result = transport.collect(binding["operation"])
        return self._result(binding["binding_id"], str(result["status"]), attempted=bool(result.get("connection_attempted")), output=str(result.get("output") or ""))

    def _execute(self, binding: dict[str, Any]) -> dict[str, Any]:
        return {"ssh": self._ssh, "winrm": self._winrm, "powershell": self._powershell, "rest": self._rest}[binding["protocol"]](binding)

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
