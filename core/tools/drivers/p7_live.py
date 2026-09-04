"""Minimal P7 protocol drivers with fail-closed identity and scope gates."""

import base64
import hashlib
import http.client
import os
import re
import ssl
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

from core.transports.credentials import CredentialResolver


class PinnedPlinkSSHTransport:
    """Execute one allowlisted read-only SSH command with a configured host-key pin."""

    HOST_KEY = re.compile(r"^ssh-[A-Za-z0-9-]+\s+\d+\s+SHA256:[A-Za-z0-9+/=]+$")

    def __init__(self, *, base_dir: Path, adapter_id: str, entity_id: str, target: str,
                 checks: dict[str, str], credential_keys: dict[str, str], host_key_pin_env: str,
                 runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
                 plink_path: Path | None = None):
        self.base_dir, self.adapter_id, self.entity_id = Path(base_dir).resolve(), adapter_id, entity_id
        self.target, self.checks, self.credential_keys = target, dict(checks), dict(credential_keys)
        self.resolver, self.runner = CredentialResolver(self.base_dir), runner
        self.pin = self.resolver.value(host_key_pin_env)
        self.plink_path = Path(plink_path or self.resolver.local.get("MNE_PLINK_PATH", r"C:\Program Files\PuTTY\plink.exe"))

    @staticmethod
    def _blocked(status: str, attempted: bool = False) -> dict[str, Any]:
        return {"status": status, "connection_attempted": attempted, "output": None, "credential_returned": False, "raw_error_returned": False}

    def __call__(self, request: dict[str, Any]) -> dict[str, Any]:
        check_id = request.get("check_id")
        if (request.get("adapter_id") != self.adapter_id or request.get("entity_id") != self.entity_id
                or request.get("target") != self.target or request.get("command") != self.checks.get(check_id)
                or request.get("simulation_mode") is not False):
            return self._blocked("SCOPE_BLOCKED")
        if not self.HOST_KEY.fullmatch(self.pin):
            return self._blocked("IDENTITY_PIN_NOT_CONFIGURED")
        if not self.plink_path.is_file():
            return self._blocked("TRANSPORT_DEPENDENCY_MISSING")
        try:
            username, password = self.resolver.resolve(target=self.target, **self.credential_keys)
        except (OSError, UnicodeError, ValueError):
            return self._blocked("CREDENTIAL_NOT_CONFIGURED")
        timeout = min(max(int(request.get("timeout_seconds", 10)), 1), 15)
        try:
            with TemporaryDirectory(prefix="mne-p7-ssh-") as directory:
                secret_file = Path(directory) / "credential.txt"
                secret_file.write_text(password + "\n", encoding="utf-8")
                try:
                    secret_file.chmod(0o600)
                except OSError:
                    pass
                process = self.runner([str(self.plink_path), "-batch", "-ssh", "-P", "22", "-hostkey", self.pin,
                                       "-l", username, "-pwfile", str(secret_file), self.target, self.checks[check_id]],
                                      check=False, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                      timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except subprocess.TimeoutExpired:
            return self._blocked("TIMEOUT", True)
        except OSError:
            return self._blocked("TRANSPORT_EXCEPTION", True)
        if process.returncode != 0:
            error = (process.stderr or "").casefold()
            status = "IDENTITY_PIN_REJECTED" if "host key" in error else ("AUTHENTICATION_FAILED" if "access denied" in error or "authentication" in error else "TRANSPORT_FAILED")
            return self._blocked(status, True)
        return {"status": "SUCCESS", "connection_attempted": True, "output": process.stdout,
                "credential_returned": False, "raw_error_returned": False}


class VerifiedHTTPTransport:
    """Bounded GET/HEAD transport requiring CA validation or an explicit SHA-256 cert pin."""

    SAFE_METHODS = {"GET", "HEAD"}
    CERT_PIN = re.compile(r"^[a-f0-9]{64}$")

    def __init__(self, *, target: str, port: int = 443, certificate_sha256: str = "", timeout_seconds: int = 15):
        self.target, self.port = target, port
        self.pin = certificate_sha256.casefold()
        self.timeout = min(max(timeout_seconds, 1), 15)

    def request(self, method: str, path: str, *, username: str = "", password: str = "") -> dict[str, Any]:
        if method not in self.SAFE_METHODS or not path.startswith("/") or any(x in path for x in ("\r", "\n")):
            return {"status": "SCOPE_BLOCKED", "connection_attempted": False}
        headers = {"Accept": "application/json", "User-Agent": "MNE-Brain-P7-ReadOnly/1.0"}
        if username or password:
            if not username or not password:
                return {"status": "CREDENTIAL_NOT_CONFIGURED", "connection_attempted": False}
            headers["Authorization"] = "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()
        context = ssl.create_default_context()
        if self.pin:
            if not self.CERT_PIN.fullmatch(self.pin):
                return {"status": "IDENTITY_PIN_NOT_CONFIGURED", "connection_attempted": False}
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        connection = http.client.HTTPSConnection(self.target, self.port, timeout=self.timeout, context=context)
        try:
            connection.connect()
            certificate = connection.sock.getpeercert(binary_form=True) if connection.sock else b""
            if self.pin and hashlib.sha256(certificate).hexdigest() != self.pin:
                return {"status": "IDENTITY_PIN_REJECTED", "connection_attempted": True}
            connection.request(method, path, headers=headers)
            response = connection.getresponse()
            body = response.read(131072 if method == "GET" else 0)
            if response.length and response.length > len(body):
                return {"status": "OUTPUT_TOO_LARGE", "connection_attempted": True}
            status = "AUTHENTICATION_FAILED" if response.status in {401, 403} else "SUCCESS"
            return {"status": status, "connection_attempted": True,
                    "output": f"HTTP {response.status}\ncontent-type: {response.getheader('content-type', '')}\n" + body.decode("utf-8", "replace"),
                    "credential_returned": False, "raw_error_returned": False}
        except ssl.SSLCertVerificationError:
            return {"status": "TLS_IDENTITY_NOT_VERIFIED", "connection_attempted": True}
        except (OSError, http.client.HTTPException):
            return {"status": "TRANSPORT_FAILED", "connection_attempted": True}
        finally:
            connection.close()


class PowerShellRemotingTransport:
    """Generate only Get-/repadmin read commands and require Kerberos or WinRM HTTPS."""

    SAFE = re.compile(r"^(?:Get-[A-Za-z0-9*_-]+(?:\s+[A-Za-z0-9,*._-]+)*|repadmin /replsummary)$")

    def readiness(self, *, target: str, command: str, use_https: bool, kerberos_identity: bool) -> dict[str, Any]:
        if not self.SAFE.fullmatch(command):
            return {"status": "SCOPE_BLOCKED", "connection_attempted": False}
        if not use_https and not kerberos_identity:
            return {"status": "KERBEROS_OR_HTTPS_REQUIRED", "connection_attempted": False}
        return {"status": "IMPLEMENTED_OWNER_GATED", "target": target, "connection_attempted": False}


class SnmpReadOnlyTransport:
    """Fail closed until SNMPv3 identity and an opaque credential mapping exist."""

    def readiness(self, *, engine_id: str = "", credential_reference: str = "") -> dict[str, Any]:
        if not engine_id:
            return {"status": "SNMP_ENGINE_ID_NOT_CONFIGURED", "connection_attempted": False}
        if not credential_reference.startswith("secretref://"):
            return {"status": "CREDENTIAL_NOT_CONFIGURED", "connection_attempted": False}
        try:
            __import__("pysnmp")
        except ImportError:
            return {"status": "TRANSPORT_DEPENDENCY_MISSING", "connection_attempted": False}
        return {"status": "IMPLEMENTED_OWNER_GATED", "connection_attempted": False}


class VMwareRestTransport(VerifiedHTTPTransport):
    """vSphere REST transport; TLS identity rules are inherited unchanged."""

    SESSION_PATH = "/rest/com/vmware/cis/session"
