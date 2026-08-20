"""Exact-scope P9 collector. Raw output exists only inside one normalization call."""

import hashlib
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

from core.tools.drivers.p7_live import PinnedPlinkSSHTransport
from core.transports.credentials import CredentialResolver
from core.transports.specialized import FMCRestTransport, KerberosPowerShellTransport, VCenterRestTransport
from core.troubleshooting.p9_engine import P9DiagnosticEngine
from core.troubleshooting.p9_normalizers import normalize_output


class P9LiveCollector:
    def __init__(self, base_dir: Path, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run):
        self.base_dir = Path(base_dir).resolve()
        self.engine = P9DiagnosticEngine(self.base_dir)
        self.credentials = CredentialResolver(self.base_dir)
        self.runner = runner

    @staticmethod
    def _public_failure(check: dict[str, Any], status: str, attempted: bool) -> dict[str, Any]:
        return {"status": status, "binding_id": check["binding_id"], "check_id": check["check_id"], "connection_attempted": attempted, "evidence": None, "raw_output_included": False, "credentials_returned": False, "persistence_attempted": False, "remediation_attempted": False}

    @staticmethod
    def _timeout_output(exc: subprocess.TimeoutExpired) -> str:
        """Recover bounded output already received before an interactive CLI stalled."""
        value = exc.stdout or ""
        if isinstance(value, bytes):
            return value.decode("utf-8", "replace")
        return str(value)

    def _ssh(self, check: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
        prefix = binding["env_prefix"]
        target = self.credentials.value(f"{prefix}_HOST")
        if " || " in check["operation"]:
            return self._ssh_interactive(check, binding, target)
        transport = PinnedPlinkSSHTransport(
            base_dir=self.base_dir, adapter_id="p9-deep-readonly", entity_id=check["binding_id"], target=target,
            checks={check["check_id"]: check["operation"]},
            credential_keys={"host_key": f"{prefix}_HOST", "username_key": f"{prefix}_USERNAME", "password_key": f"{prefix}_PASSWORD"},
            host_key_pin_env=f"{prefix}_SSH_HOSTKEY", runner=self.runner,
        )
        result = transport({"adapter_id": "p9-deep-readonly", "entity_id": check["binding_id"], "target": target, "check_id": check["check_id"], "command": check["operation"], "simulation_mode": False, "timeout_seconds": int(self.engine.policy["timeout_seconds"])})
        if binding["platform"] in ("cisco_ftd", "cisco_fmc", "storage_or_switch", "fujitsu_switch", "zyxel_switch"):
            output = str(result.get("output") or "")
            low_signal = True
            if result.get("status") == "SUCCESS" and output.strip():
                observations, _ = normalize_output(check["normalizer"], output)
                low_signal = observations.get("signal_quality") == "LOW"
            if result.get("status") != "SUCCESS" or not output.strip() or low_signal:
                return self._ssh_interactive(check, binding, target)
        return result

    def _ssh_interactive(self, check: dict[str, Any], binding: dict[str, Any], target: str) -> dict[str, Any]:
        prefix = binding["env_prefix"]
        pin = self.credentials.value(f"{prefix}_SSH_HOSTKEY")
        try:
            username, password = self.credentials.resolve(target=target, host_key=f"{prefix}_HOST", username_key=f"{prefix}_USERNAME", password_key=f"{prefix}_PASSWORD")
        except ValueError:
            return {"status": "CREDENTIAL_NOT_CONFIGURED", "connection_attempted": False, "output": None}
        plink = Path(self.credentials.local.get("MNE_PLINK_PATH", r"C:\Program Files\PuTTY\plink.exe"))
        if not plink.is_file() or not pin:
            return {"status": "TRANSPORT_DEPENDENCY_MISSING", "connection_attempted": False, "output": None}
        commands = check["operation"].split(" || ")
        exits = ["exit"] if binding["platform"] == "fujitsu_switch" else ["exit", "exit"]
        input_text = "\n".join(commands + exits) + "\n"
        try:
            with TemporaryDirectory(prefix="mne-p9-ssh-") as directory:
                password_file = Path(directory) / "credential.txt"
                password_file.write_text(password + "\n", encoding="utf-8")
                try:
                    password_file.chmod(0o600)
                except OSError:
                    pass
                process = self.runner([str(plink), "-batch", "-no-antispoof", "-ssh", "-t", "-P", "22", "-hostkey", pin, "-l", username, "-pwfile", str(password_file), target], input=input_text, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=int(self.engine.policy["timeout_seconds"]), creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except subprocess.TimeoutExpired as exc:
            partial = self._timeout_output(exc)
            if partial.strip():
                return {"status": "SUCCESS", "connection_attempted": True, "output": partial, "collection_complete": False}
            return {"status": "TIMEOUT", "connection_attempted": True, "output": None}
        except OSError:
            return {"status": "TRANSPORT_EXCEPTION", "connection_attempted": True, "output": None}
        if process.returncode != 0:
            return {"status": "TRANSPORT_FAILED", "connection_attempted": True, "output": None}
        return {"status": "SUCCESS", "connection_attempted": True, "output": process.stdout or ""}

    def _winrm(self, check: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
        return KerberosPowerShellTransport(self.base_dir, self.runner, timeout=int(self.engine.policy["timeout_seconds"])).collect(
            prefix=binding["env_prefix"], target=binding["kerberos_fqdn"], operation=check["operation"]
        )

    def _powershell(self, check: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
        return KerberosPowerShellTransport(self.base_dir, self.runner, timeout=int(self.engine.policy["timeout_seconds"])).collect(
            prefix=binding["env_prefix"], target=binding["kerberos_fqdn"], operation=check["operation"],
            exchange_endpoint=binding.get("endpoint_path", ""),
        )

    def _rest(self, check: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
        timeout = int(self.engine.policy["timeout_seconds"])
        if binding["platform"] == "vmware_vcenter":
            return VCenterRestTransport(self.base_dir, timeout=timeout).collect(check["operation"])
        if binding["platform"] == "cisco_fmc":
            return FMCRestTransport(self.base_dir, timeout=timeout).collect(check["operation"])
        return {"status": "UNSUPPORTED_REST_PLATFORM", "connection_attempted": False, "output": None}

    def collect(self, *, scenario_id: str, primary_binding: str, check_id: str, owner_proceed: bool) -> dict[str, Any]:
        checks = {item["check_id"]: item for item in self.engine.resolved_checks(scenario_id, primary_binding)}
        check = checks.get(check_id)
        if check is None:
            return {"status": "NOT_RUN", "reason": "EXACT_REGISTERED_CHECK_REQUIRED", "connection_attempted": False, "evidence": None}
        if not owner_proceed:
            return {"status": "NOT_RUN", "reason": "OWNER_PROCEED_REQUIRED", "binding_id": check["binding_id"], "check_id": check_id, "connection_attempted": False, "evidence": None}
        binding = self.engine.bindings[check["binding_id"]]
        collectors = {"ssh": self._ssh, "winrm": self._winrm, "powershell": self._powershell, "rest": self._rest}
        result = collectors[binding["protocol"]](check, binding)
        status, attempted = str(result.get("status", "TRANSPORT_FAILED")), bool(result.get("connection_attempted"))
        if status != "SUCCESS":
            return self._public_failure(check, status, attempted)
        output = str(result.get("output") or "")
        encoded = output.encode("utf-8", "replace")
        if not encoded or len(encoded) > int(self.engine.policy["max_output_bytes"]):
            return self._public_failure(check, "EMPTY_OR_OVERSIZED_OUTPUT", attempted)
        lowered = output.casefold()
        if any(marker in lowered for marker in ("unknown command", "invalid input", "command not found", "unrecognized command", "incomplete command")):
            return self._public_failure(check, "COMMAND_REJECTED", attempted)
        try:
            observations, summary = normalize_output(check["normalizer"], output)
        finally:
            output = ""
        if observations.get("signal_quality") == "LOW":
            return self._public_failure(check, "NORMALIZATION_INSUFFICIENT", attempted)
        observations["collection_complete"] = bool(result.get("collection_complete", True))
        collected_at = datetime.now(timezone.utc).isoformat()
        material = f"{scenario_id}|{check['binding_id']}|{check_id}|{collected_at}|{hashlib.sha256(encoded).hexdigest()}"
        evidence = {
            "evidence_id": "p9-live-" + hashlib.sha256(material.encode()).hexdigest()[:16],
            "binding_id": check["binding_id"], "check_id": check_id,
            "collected_at": collected_at, "verification_status": "live_verified", "trust_level": 5,
            "outcome": "SUCCESS", "summary": summary or "Read-only check returned normalized evidence.",
            "observations": observations, "output_sha256_prefix": hashlib.sha256(encoded).hexdigest()[:16],
        }
        return {"status": "SUCCESS", "binding_id": check["binding_id"], "check_id": check_id, "connection_attempted": True, "evidence": evidence, "raw_output_included": False, "credentials_returned": False, "persistence_attempted": False, "remediation_attempted": False}
