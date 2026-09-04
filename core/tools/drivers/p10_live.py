"""Real P10 transports guarded by exact bindings, pins, and write credentials."""

from __future__ import annotations

import base64
import hashlib
import http.client
import json
import os
import re
import ssl
import subprocess
import threading
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

import yaml

from core.execution.p10_commands import P10CommandError, render_read_wire, render_wire
from core.transports.credentials import CredentialResolver
from core.transports.specialized import KerberosPowerShellTransport, PinnedJSONHTTPSClient


class P10LiveDriverError(RuntimeError):
    pass


class P10LivePlatformDriver:
    """Submit one already-approved transaction with no automatic retry."""

    live = True
    simulation = False
    _PIN = re.compile(r"^[a-fA-F0-9]{64}$")
    _HOSTKEY = re.compile(r"^ssh-[A-Za-z0-9-]+\s+\d+\s+SHA256:[A-Za-z0-9+/=]+$")
    _USERNAME = re.compile(r"^[A-Za-z0-9_.@\\-]{1,128}$")
    _FAIL_MARKERS = ("invalid input", "unknown command", "command not found", "permission denied", "authorization failed")

    def __init__(
        self,
        base_dir: Path,
        *,
        platform: str,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ):
        self.base_dir = Path(base_dir).resolve()
        self.platform = platform
        self.credentials = CredentialResolver(self.base_dir)
        self.bindings = {
            item["binding_id"]: item
            for item in (yaml.safe_load((self.base_dir / "config/p7_device_bindings.yaml").read_text(encoding="utf-8")) or {}).get("bindings", [])
        }
        self.platforms = (yaml.safe_load((self.base_dir / "config/p10_platform_registry.yaml").read_text(encoding="utf-8")) or {}).get("platforms", {})
        self.runner = runner or subprocess.run
        self._active: dict[str, subprocess.Popen[str]] = {}
        self._authorized: set[tuple[str, str]] = set()
        self._lock = threading.RLock()

    def _binding(self, binding_id: str, target: str) -> tuple[dict[str, Any], str]:
        binding = self.bindings.get(binding_id)
        policy = self.platforms.get(self.platform)
        if not binding or not policy or binding.get("scope_status") != "ACTIVE":
            raise P10LiveDriverError("Exact active platform binding is unavailable.")
        if binding.get("platform") not in policy.get("p7_platforms", []):
            raise P10LiveDriverError("Binding platform mismatch.")
        prefix = str(binding["env_prefix"])
        configured_target = str(binding.get("kerberos_fqdn") or self.credentials.value(f"{prefix}_HOST") or binding.get("target", ""))
        if not configured_target or configured_target != target:
            raise P10LiveDriverError("Exact configured target mismatch.")
        return binding, prefix

    def _write_credentials(self, prefix: str) -> tuple[str, str, str]:
        reference = self.credentials.value(f"{prefix}_WRITE_CREDENTIAL_REF")
        username = self.credentials.value(f"{prefix}_WRITE_USERNAME")
        password = self.credentials.value(f"{prefix}_WRITE_PASSWORD")
        if not reference.startswith("secretref://") or not self._USERNAME.fullmatch(username) or not password:
            raise P10LiveDriverError(f"Separate write authorization is not configured: {prefix}_WRITE_CREDENTIAL_REF")
        return reference, username, password

    def _read_credentials(self, prefix: str) -> tuple[str, str]:
        try:
            return self.credentials.resolve_pair(username_key=f"{prefix}_USERNAME", password_key=f"{prefix}_PASSWORD")
        except ValueError as exc:
            raise P10LiveDriverError(f"Read credential is not configured for {prefix}.") from exc

    @staticmethod
    def _safe_result(status: str, *, attempted: bool, submitted: bool, transaction_id: str = "", output: str = "") -> dict[str, Any]:
        encoded = output.encode("utf-8", "replace")
        result = {
            "status": status,
            "connection_attempted": attempted,
            "submitted": submitted,
            "output": None,
            "output_bytes": len(encoded),
            "output_sha256_prefix": hashlib.sha256(encoded).hexdigest()[:16] if encoded else "",
            "automatic_retries": 0,
        }
        if transaction_id:
            result["transaction_id"] = transaction_id
        return result

    def readiness(self, *, binding_id: str, target: str) -> dict[str, Any]:
        try:
            binding, prefix = self._binding(binding_id, target)
            self._write_credentials(prefix)
        except P10LiveDriverError as exc:
            return {"status": "BLOCKED", "reason": str(exc), "connection_attempted": False, "write_authorized": False}
        identity_key = f"{prefix}_TLS_CERT_SHA256" if binding.get("identity_mode") == "PINNED_TLS_CERT" else f"{prefix}_SSH_HOSTKEY"
        identity = self.credentials.value(identity_key)
        valid = bool(binding.get("kerberos_fqdn")) if binding.get("identity_mode") == "KERBEROS_FQDN" else bool(identity)
        return {
            "status": "READY_FOR_AUTH_PROBE" if valid else "BLOCKED",
            "reason": "SAFE_LIVE_AUTH_PROBE_NOT_RUN" if valid else f"Identity pin is not configured: {identity_key}",
            "connection_attempted": False,
            "write_authorized": False,
        }

    def probe_write_authorization(self, *, binding_id: str, target: str, timeout_seconds: int = 15) -> dict[str, Any]:
        """Use the write credential for a read-only role/privilege query."""
        try:
            binding, prefix = self._binding(binding_id, target)
            _, username, password = self._write_credentials(prefix)
        except P10LiveDriverError as exc:
            return {"status": "BLOCKED", "reason": str(exc), "connection_attempted": False, "write_authorized": False}
        probe = str(self.platforms[self.platform].get("privilege_probe", ""))
        if not probe:
            return {"status": "AUTHORIZATION_PROBE_UNAVAILABLE", "connection_attempted": False, "write_authorized": False}
        if self.platform == "vmware_vcenter":
            return {"status": "AUTHORIZATION_PROBE_UNAVAILABLE", "reason": "A decisive bounded vCenter privilege query is not configured.", "connection_attempted": False, "write_authorized": False}
        if self.platform in {"cisco_fmc"}:
            wire = {"protocol": "https_read", "method": "GET", "path": probe[4:] if probe.startswith("GET ") else probe, "body": None, "display": [probe]}
            result = self._https_read(prefix, target, username, password, wire, timeout_seconds)
        elif self.platform == "windows_powershell":
            result = self._winrm_read_with_credentials(target, username, password, probe, timeout_seconds)
        else:
            command = probe
            if self.platform == "f5_bigip": command = f"tmsh -q -c 'list auth user {username} one-line'"
            elif self.platform == "fortinet_fortios": command = f"show system admin {username}"
            result = self._ssh_read(prefix, target, username, password, {"commands": [command]}, timeout_seconds)
        output = str(result.pop("output", "") or "")
        lowered = output.casefold()
        authorized = False
        if result.get("status") == "SUCCESS":
            if self.platform == "fortinet_fortios": authorized = "super_admin" in lowered
            elif self.platform == "f5_bigip": authorized = "role administrator" in lowered
            elif self.platform in {"cisco_switching", "fujitsu_switching"}: authorized = bool(re.search(r"privilege\s+level\s+(?:is\s+)?15\b", lowered))
            elif self.platform == "linux_host": authorized = "(all" in lowered and "not allowed" not in lowered
            elif self.platform == "windows_powershell": authorized = "s-1-5-32-544" in lowered
            elif self.platform == "cisco_fmc": authorized = '"admin"' in lowered or '"administrator"' in lowered
        if authorized:
            self._authorized.add((binding_id, target))
        return {"status": "WRITE_AUTHORIZED" if authorized else "WRITE_AUTHORIZATION_NOT_CONFIRMED", "connection_attempted": bool(result.get("connection_attempted")),
                "write_authorized": authorized, "credential_reference": f"{prefix}_WRITE_CREDENTIAL_REF", "raw_output_included": False}

    def capture_state(self, *, binding_id: str, target: str, commands: list[dict[str, Any]], timeout_seconds: int, postcheck: bool = False) -> dict[str, Any]:
        """Run one exact read-only query and return only normalized verification metadata."""
        if len(commands) != 1 or not isinstance(commands[0].get("transaction"), dict):
            return {"status": "SCOPE_BLOCKED", "connection_attempted": False}
        binding, prefix = self._binding(binding_id, target)
        username, password = self._read_credentials(prefix)
        transaction = commands[0]["transaction"]
        try:
            wire = render_read_wire(transaction)
        except P10CommandError:
            return {"status": "EXACT_STATE_PROBE_NOT_IMPLEMENTED", "connection_attempted": False}
        if wire["protocol"] == "ssh_read":
            collected = self._ssh_read(prefix, target, username, password, wire, timeout_seconds)
        elif wire["protocol"] == "winrm_read":
            result = KerberosPowerShellTransport(self.base_dir, timeout=timeout_seconds).collect(prefix=prefix, target=target, operation=wire["commands"][0], exchange_endpoint=binding.get("endpoint_path", ""))
            collected = {"status": result.get("status"), "connection_attempted": result.get("connection_attempted"), "output": result.get("output") or ""}
        else:
            collected = self._https_read(prefix, target, username, password, wire, timeout_seconds)
        output = str(collected.pop("output", "") or "")
        successful_state = collected.get("status") in {"SUCCESS", "SUCCESS_ABSENT"}
        state_digest = hashlib.sha256(output.encode("utf-8", "replace")).hexdigest() if successful_state else ""
        identity_key = f"{prefix}_TLS_CERT_SHA256" if binding.get("identity_mode") == "PINNED_TLS_CERT" else f"{prefix}_SSH_HOSTKEY"
        if binding.get("identity_mode") == "KERBEROS_FQDN": identity_key = str(binding.get("kerberos_fqdn"))
        effect_verified = self._effect_verified(transaction, output, absent=collected.get("status") == "SUCCESS_ABSENT") if postcheck and successful_state else False
        return {**collected, "state_digest": state_digest, "identity_pin": self.credentials.value(identity_key) if "_" in identity_key else identity_key,
                "effect_verified": effect_verified, "output_included": False}

    def _ssh_read(self, prefix: str, target: str, username: str, password: str, wire: dict[str, Any], timeout: int) -> dict[str, Any]:
        pin = self.credentials.value(f"{prefix}_SSH_HOSTKEY")
        plink = Path(self.credentials.local.get("MNE_PLINK_PATH", r"C:\Program Files\PuTTY\plink.exe"))
        if not self._HOSTKEY.fullmatch(pin) or not plink.is_file():
            return {"status": "IDENTITY_OR_DEPENDENCY_NOT_CONFIGURED", "connection_attempted": False, "output": ""}
        with TemporaryDirectory(prefix="mne-p10-read-") as directory:
            password_file = Path(directory) / "credential.txt"; password_file.write_text(password + "\n", encoding="utf-8")
            try: password_file.chmod(0o600)
            except OSError: pass
            args = [str(plink), "-batch", "-no-antispoof", "-ssh", "-P", "22", "-hostkey", pin, "-l", username, "-pwfile", str(password_file), target, wire["commands"][0]]
            try:
                result = self.runner(args, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=min(max(int(timeout), 1), 120), creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            except subprocess.TimeoutExpired:
                return {"status": "TIMEOUT", "connection_attempted": True, "output": ""}
            except OSError:
                return {"status": "TRANSPORT_FAILED", "connection_attempted": True, "output": ""}
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        lowered = output.casefold()
        absent = result.returncode != 0 and any(marker in lowered for marker in ("not found", "does not exist", "not configured", "was not found"))
        return {"status": "SUCCESS_ABSENT" if absent else ("SUCCESS" if result.returncode == 0 else "READ_FAILED"), "connection_attempted": True, "output": output}

    def _https_read(self, prefix: str, target: str, username: str, password: str, wire: dict[str, Any], timeout: int) -> dict[str, Any]:
        pin = self.credentials.value(f"{prefix}_TLS_CERT_SHA256")
        client = PinnedJSONHTTPSClient(target, pin, timeout=timeout)
        basic = base64.b64encode(f"{username}:{password}".encode()).decode()
        if self.platform == "cisco_fmc":
            auth = client.request("POST", "/api/fmc_platform/v1/auth/generatetoken", headers={"Authorization": f"Basic {basic}"})
            headers = auth.get("headers") or {}; token = headers.get("x-auth-access-token", ""); domain = headers.get("domain_uuid", "") or headers.get("domain-uuid", "")
            if auth.get("status") != "SUCCESS" or not token or not domain:
                return {"status": "AUTHORIZATION_FAILED", "connection_attempted": bool(auth.get("connection_attempted")), "output": ""}
            result = client.request("GET", wire["path"].replace("{domainUUID}", domain), headers={"X-auth-access-token": token})
        else:
            auth = client.request("POST", "/api/session", headers={"Authorization": f"Basic {basic}"})
            if auth.get("status") != "SUCCESS":
                return {"status": "AUTHORIZATION_FAILED", "connection_attempted": bool(auth.get("connection_attempted")), "output": ""}
            try:
                token = json.loads(str(auth.get("body") or "")); token = token.get("value", "") if isinstance(token, dict) else token
            except (ValueError, json.JSONDecodeError):
                return {"status": "AUTHENTICATION_FAILED", "connection_attempted": True, "output": ""}
            result = client.request("GET", wire["path"], headers={"vmware-api-session-id": str(token).strip('"')})
        return {"status": result.get("status"), "connection_attempted": result.get("connection_attempted"), "output": result.get("body") or ""}

    def _winrm_read_with_credentials(self, target: str, username: str, password: str, operation: str, timeout: int) -> dict[str, Any]:
        operation_b64 = base64.b64encode(operation.encode("utf-16le")).decode("ascii")
        safe_target = target.replace("'", "''")
        script = (
            "$ErrorActionPreference='Stop';$s=$null;try {"
            "$secure=ConvertTo-SecureString $env:MNE_P10_PASSWORD -AsPlainText -Force;"
            "$cred=New-Object System.Management.Automation.PSCredential($env:MNE_P10_USERNAME,$secure);"
            f"$s=New-PSSession -ComputerName '{safe_target}' -Credential $cred -Authentication Negotiate;"
            f"$op=[ScriptBlock]::Create([Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('{operation_b64}')));"
            "Invoke-Command -Session $s -ScriptBlock $op} finally {if($s){Remove-PSSession $s}}"
        )
        env = os.environ.copy(); env["MNE_P10_USERNAME"] = username; env["MNE_P10_PASSWORD"] = password
        try:
            result = self.runner(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", "-"], input=script,
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=min(max(int(timeout), 1), 120), env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except subprocess.TimeoutExpired:
            return {"status": "TIMEOUT", "connection_attempted": True, "output": ""}
        except OSError:
            return {"status": "TRANSPORT_FAILED", "connection_attempted": True, "output": ""}
        return {"status": "SUCCESS" if result.returncode == 0 else "READ_FAILED", "connection_attempted": True, "output": (result.stdout or "") + "\n" + (result.stderr or "")}

    @staticmethod
    def _effect_verified(transaction: dict[str, Any], output: str, *, absent: bool = False) -> bool:
        lowered = output.casefold()
        action = str(transaction.get("action", ""))
        if action.startswith(("delete_", "remove_")):
            return absent or any(marker in lowered for marker in ("not found", "does not exist", '"items":[]'))
        if not output.strip(): return False
        if action in {"start_service", "start_site", "start_app_pool", "power_on", "enable_user", "enable_member", "enable_virtual_server", "no_shutdown_port"}:
            return any(marker in lowered for marker in ("running", "started", "enabled", "active", "up"))
        if action in {"stop_site", "power_off", "disable_user", "disable_member", "disable_virtual_server", "shutdown_port"}:
            return any(marker in lowered for marker in ("stopped", "disabled", "inactive", "down"))
        return True

    def execute(self, *, binding_id: str, target: str, commands: list[dict[str, Any]], timeout_seconds: int) -> dict[str, Any]:
        if len(commands) != 1:
            raise P10LiveDriverError("Exactly one typed transaction is allowed.")
        binding, prefix = self._binding(binding_id, target)
        _, username, password = self._write_credentials(prefix)
        if (binding_id, target) not in self._authorized:
            raise P10LiveDriverError("Write authorization was not established by the current in-memory privilege probe.")
        item = commands[0]
        transaction = item.get("transaction")
        if not isinstance(transaction, dict) or transaction.get("platform") != self.platform or transaction.get("target") != target:
            raise P10LiveDriverError("Approved transaction envelope mismatch.")
        try:
            expected_wire = render_wire(transaction)
        except P10CommandError as exc:
            raise P10LiveDriverError(str(exc)) from exc
        if item.get("wire") != expected_wire or item.get("display") != expected_wire["display"][0]:
            raise P10LiveDriverError("Approved display and executable transaction differ.")
        protocol = expected_wire["protocol"]
        if protocol == "ssh_cli":
            return self._ssh(binding, prefix, target, username, password, expected_wire, timeout_seconds)
        if protocol == "winrm_powershell":
            return self._winrm(binding, target, username, password, expected_wire, timeout_seconds)
        if protocol == "https_json":
            return self._https(binding, prefix, target, username, password, expected_wire, timeout_seconds)
        raise P10LiveDriverError("Unsupported live protocol.")

    def _ssh(self, binding: dict[str, Any], prefix: str, target: str, username: str, password: str, wire: dict[str, Any], timeout: int) -> dict[str, Any]:
        pin = self.credentials.value(f"{prefix}_SSH_HOSTKEY")
        plink = Path(self.credentials.local.get("MNE_PLINK_PATH", r"C:\Program Files\PuTTY\plink.exe"))
        if not self._HOSTKEY.fullmatch(pin) or not plink.is_file():
            return self._safe_result("IDENTITY_OR_DEPENDENCY_NOT_CONFIGURED", attempted=False, submitted=False)
        transaction_id = f"p10-tx-{uuid.uuid4().hex[:16]}"
        with TemporaryDirectory(prefix="mne-p10-write-") as directory:
            password_file = Path(directory) / "credential.txt"
            password_file.write_text(password + "\n", encoding="utf-8")
            try: password_file.chmod(0o600)
            except OSError: pass
            args = [str(plink), "-batch", "-no-antispoof", "-ssh", "-P", "22", "-hostkey", pin, "-l", username, "-pwfile", str(password_file), target]
            script = "\n".join(wire["commands"]) + "\nexit\n"
            try:
                process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    encoding="utf-8", errors="replace", creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                with self._lock: self._active[transaction_id] = process
                stdout, stderr = process.communicate(script, timeout=min(max(int(timeout), 1), 120))
            except subprocess.TimeoutExpired:
                process.terminate()
                return self._safe_result("TIMEOUT", attempted=True, submitted=True, transaction_id=transaction_id)
            except OSError:
                return self._safe_result("TRANSPORT_FAILED", attempted=True, submitted=False, transaction_id=transaction_id)
            finally:
                with self._lock: self._active.pop(transaction_id, None)
        output = (stdout or "") + "\n" + (stderr or "")
        lowered = output.casefold()
        status = "COMMITTED" if process.returncode == 0 and not any(marker in lowered for marker in self._FAIL_MARKERS) else "FAILED"
        return self._safe_result(status, attempted=True, submitted=True, transaction_id=transaction_id, output=output)

    def _winrm(self, binding: dict[str, Any], target: str, username: str, password: str, wire: dict[str, Any], timeout: int) -> dict[str, Any]:
        del binding
        operation = wire["commands"][0]
        operation_b64 = base64.b64encode(operation.encode("utf-16le")).decode("ascii")
        safe_target = target.replace("'", "''")
        script = (
            "$ErrorActionPreference='Stop';$s=$null;try {"
            "$secure=ConvertTo-SecureString $env:MNE_P10_PASSWORD -AsPlainText -Force;"
            "$cred=New-Object System.Management.Automation.PSCredential($env:MNE_P10_USERNAME,$secure);"
            f"$s=New-PSSession -ComputerName '{safe_target}' -Credential $cred -Authentication Negotiate;"
            f"$op=[ScriptBlock]::Create([Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('{operation_b64}')));"
            "Invoke-Command -Session $s -ScriptBlock $op} finally {if($s){Remove-PSSession $s}}"
        )
        environment = os.environ.copy(); environment["MNE_P10_USERNAME"] = username; environment["MNE_P10_PASSWORD"] = password
        transaction_id = f"p10-tx-{uuid.uuid4().hex[:16]}"
        try:
            result = self.runner(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", "-"],
                input=script, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=min(max(int(timeout), 1), 120),
                env=environment, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except subprocess.TimeoutExpired:
            return self._safe_result("TIMEOUT", attempted=True, submitted=True, transaction_id=transaction_id)
        except OSError:
            return self._safe_result("TRANSPORT_FAILED", attempted=True, submitted=False, transaction_id=transaction_id)
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        return self._safe_result("COMMITTED" if result.returncode == 0 else "FAILED", attempted=True, submitted=True, transaction_id=transaction_id, output=output)

    def _https(self, binding: dict[str, Any], prefix: str, target: str, username: str, password: str, wire: dict[str, Any], timeout: int) -> dict[str, Any]:
        del binding
        pin = self.credentials.value(f"{prefix}_TLS_CERT_SHA256")
        if not self._PIN.fullmatch(pin):
            return self._safe_result("IDENTITY_PIN_NOT_CONFIGURED", attempted=False, submitted=False)
        context = ssl.create_default_context(); context.check_hostname = False; context.verify_mode = ssl.CERT_NONE
        transaction_id = f"p10-tx-{uuid.uuid4().hex[:16]}"
        connection = http.client.HTTPSConnection(target, 443, timeout=min(max(int(timeout), 1), 120), context=context)
        submitted = False
        try:
            connection.connect()
            certificate = connection.sock.getpeercert(binary_form=True) if connection.sock else b""
            if not certificate or hashlib.sha256(certificate).hexdigest() != pin.casefold():
                return self._safe_result("IDENTITY_PIN_REJECTED", attempted=True, submitted=False, transaction_id=transaction_id)
            headers = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "MNE-Brain-P10/1.0"}
            path = wire["path"]
            if self.platform == "cisco_fmc":
                basic = base64.b64encode(f"{username}:{password}".encode()).decode()
                connection.request("POST", "/api/fmc_platform/v1/auth/generatetoken", headers={**headers, "Authorization": f"Basic {basic}"})
                auth = connection.getresponse(); auth.read(131073)
                token = auth.getheader("X-auth-access-token", ""); domain = auth.getheader("DOMAIN_UUID", "")
                if auth.status not in range(200, 300) or not token or not domain:
                    return self._safe_result("AUTHORIZATION_FAILED", attempted=True, submitted=False, transaction_id=transaction_id)
                headers["X-auth-access-token"] = token; path = path.replace("{domainUUID}", domain)
            elif self.platform == "vmware_vcenter":
                basic = base64.b64encode(f"{username}:{password}".encode()).decode()
                connection.request("POST", "/api/session", headers={**headers, "Authorization": f"Basic {basic}"})
                auth = connection.getresponse(); body = auth.read(131073)
                if auth.status not in range(200, 300):
                    return self._safe_result("AUTHORIZATION_FAILED", attempted=True, submitted=False, transaction_id=transaction_id)
                token = json.loads(body.decode("utf-8", "replace"))
                if isinstance(token, dict): token = token.get("value", "")
                headers["vmware-api-session-id"] = str(token).strip('"')
            payload = None if wire.get("body") is None else json.dumps(wire["body"], separators=(",", ":"))
            connection.request(wire["method"], path, body=payload, headers=headers); submitted = True
            response = connection.getresponse(); output = response.read(131073).decode("utf-8", "replace")
            status = "COMMITTED" if 200 <= response.status < 300 else "FAILED"
            return self._safe_result(status, attempted=True, submitted=submitted, transaction_id=transaction_id, output=output)
        except (OSError, ssl.SSLError, http.client.HTTPException, ValueError, json.JSONDecodeError):
            return self._safe_result("UNCERTAIN" if submitted else "TRANSPORT_FAILED", attempted=True, submitted=submitted, transaction_id=transaction_id)
        finally:
            connection.close()

    def abort(self, *, transaction_id: str) -> dict[str, Any]:
        with self._lock:
            process = self._active.get(transaction_id)
        if process is None:
            return {"status": "ABORT_UNAVAILABLE", "connection_attempted": False}
        try:
            process.terminate()
            return {"status": "ABORTED", "connection_attempted": True}
        except OSError:
            return {"status": "ABORT_UNAVAILABLE", "connection_attempted": True}
