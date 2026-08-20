"""Bounded identity-pinned transports for P9 infrastructure diagnostics."""

import base64
import hashlib
import http.client
import json
import os
import re
import ssl
import subprocess
from pathlib import Path
from typing import Any, Callable

from core.transports.credentials import CredentialResolver


class PinnedJSONHTTPSClient:
    """Small HTTPS client that accepts only a preconfigured SHA-256 certificate pin."""

    CERT_PIN = re.compile(r"^[a-fA-F0-9]{64}$")
    MAX_BODY = 131072

    def __init__(self, host: str, pin: str, *, timeout: int = 15):
        self.host = host
        self.pin = pin.casefold()
        self.timeout = min(max(int(timeout), 1), 30)

    def request(self, method: str, path: str, *, headers: dict[str, str] | None = None) -> dict[str, Any]:
        if method not in {"GET", "POST"} or not path.startswith("/") or any(item in path for item in ("\r", "\n")):
            return {"status": "SCOPE_BLOCKED", "connection_attempted": False}
        if not self.host or not self.CERT_PIN.fullmatch(self.pin):
            return {"status": "TARGET_OR_IDENTITY_NOT_CONFIGURED", "connection_attempted": False}
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        connection = http.client.HTTPSConnection(self.host, 443, timeout=self.timeout, context=context)
        try:
            connection.connect()
            certificate = connection.sock.getpeercert(binary_form=True) if connection.sock else b""
            if not certificate or hashlib.sha256(certificate).hexdigest() != self.pin:
                return {"status": "IDENTITY_PIN_REJECTED", "connection_attempted": True}
            safe_headers = {"Accept": "application/json", "User-Agent": "MNE-Brain-ReadOnly/1.0"}
            safe_headers.update(headers or {})
            connection.request(method, path, headers=safe_headers)
            response = connection.getresponse()
            body = response.read(self.MAX_BODY + 1)
            if len(body) > self.MAX_BODY:
                return {"status": "OUTPUT_TOO_LARGE", "connection_attempted": True}
            return {
                "status": "SUCCESS" if 200 <= response.status < 300 else "HTTP_FAILED",
                "connection_attempted": True,
                "http_status": response.status,
                "headers": {key.casefold(): value for key, value in response.getheaders()},
                "body": body.decode("utf-8", "replace"),
            }
        except (OSError, ssl.SSLError, http.client.HTTPException):
            return {"status": "TRANSPORT_FAILED", "connection_attempted": True}
        finally:
            connection.close()


class VCenterRestTransport:
    """Authenticate to vCenter and execute one exact allowlisted REST GET."""

    def __init__(self, base_dir: Path, *, timeout: int = 15):
        self.credentials = CredentialResolver(base_dir)
        self.timeout = timeout

    def collect(self, operation: str) -> dict[str, Any]:
        if not operation.startswith("GET /rest/vcenter/"):
            return {"status": "SCOPE_BLOCKED", "connection_attempted": False, "output": None}
        host = self.credentials.value("MNE_VCENTER_HOST")
        pin = self.credentials.value("MNE_VCENTER_TLS_CERT_SHA256")
        try:
            username, password = self.credentials.resolve_pair(username_key="MNE_VCENTER_USERNAME", password_key="MNE_VCENTER_PASSWORD")
        except ValueError:
            return {"status": "CREDENTIAL_NOT_CONFIGURED", "connection_attempted": False, "output": None}
        client = PinnedJSONHTTPSClient(host, pin, timeout=self.timeout)
        basic = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        authenticated = client.request("POST", "/rest/com/vmware/cis/session", headers={"Authorization": f"Basic {basic}"})
        if authenticated.get("status") != "SUCCESS":
            return {"status": str(authenticated.get("status")), "connection_attempted": bool(authenticated.get("connection_attempted")), "output": None}
        try:
            token = str(json.loads(str(authenticated.get("body") or "{}"))["value"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return {"status": "AUTHENTICATION_FAILED", "connection_attempted": True, "output": None}
        result = client.request("GET", operation[4:], headers={"vmware-api-session-id": token})
        if result.get("status") != "SUCCESS":
            status = str(result.get("status"))
            if status == "HTTP_FAILED" and "unauthorized" in str(result.get("body") or "").casefold():
                status = "AUTHORIZATION_FAILED"
            return {"status": status, "connection_attempted": True, "output": None}
        return {"status": "SUCCESS", "connection_attempted": True, "output": str(result.get("body") or "")}


class FMCRestTransport:
    """Authenticate to FMC and execute one exact allowlisted inventory GET."""

    SAFE_PATH = re.compile(r"^/api/fmc_(?:platform|config)/v1/[A-Za-z0-9_?=&{}./-]+$")

    def __init__(self, base_dir: Path, *, timeout: int = 15):
        self.credentials = CredentialResolver(base_dir)
        self.timeout = timeout

    def collect(self, operation: str) -> dict[str, Any]:
        if not operation.startswith("GET ") or not self.SAFE_PATH.fullmatch(operation[4:]):
            return {"status": "SCOPE_BLOCKED", "connection_attempted": False, "output": None}
        host = self.credentials.value("MNE_FMC_HOST")
        pin = self.credentials.value("MNE_FMC_TLS_CERT_SHA256")
        try:
            username, password = self.credentials.resolve_pair(username_key="MNE_FMC_USERNAME", password_key="MNE_FMC_PASSWORD")
        except ValueError:
            return {"status": "CREDENTIAL_NOT_CONFIGURED", "connection_attempted": False, "output": None}
        client = PinnedJSONHTTPSClient(host, pin, timeout=self.timeout)
        basic = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        authenticated = client.request("POST", "/api/fmc_platform/v1/auth/generatetoken", headers={"Authorization": f"Basic {basic}"})
        if authenticated.get("status") != "SUCCESS":
            status = "API_ACCESS_DENIED" if authenticated.get("http_status") in (401, 403) else str(authenticated.get("status"))
            return {"status": status, "connection_attempted": bool(authenticated.get("connection_attempted")), "output": None}
        response_headers = authenticated.get("headers") or {}
        token = str(response_headers.get("x-auth-access-token") or "")
        domain = str(response_headers.get("domain_uuid") or response_headers.get("domain-uuid") or "")
        if not token or not domain:
            return {"status": "AUTHENTICATION_FAILED", "connection_attempted": True, "output": None}
        headers = {"X-auth-access-token": token}
        path = operation[4:].replace("{domainUUID}", domain)
        if "{deviceUUID}" in path:
            inventory_path = f"/api/fmc_config/v1/domain/{domain}/devices/devicerecords?expanded=true"
            inventory = client.request("GET", inventory_path, headers=headers)
            if inventory.get("status") != "SUCCESS":
                return {"status": str(inventory.get("status")), "connection_attempted": True, "output": None}
            try:
                items = json.loads(str(inventory.get("body") or "{}"))["items"]
                device_id = str(items[0]["id"])
            except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                return {"status": "DEVICE_ID_UNAVAILABLE", "connection_attempted": True, "output": None}
            path = path.replace("{deviceUUID}", device_id)
        result = client.request("GET", path, headers=headers)
        if result.get("status") != "SUCCESS":
            return {"status": str(result.get("status")), "connection_attempted": True, "output": None}
        return {"status": "SUCCESS", "connection_attempted": True, "output": str(result.get("body") or "")}


class KerberosPowerShellTransport:
    """Execute a bounded script inside an exact Kerberos WinRM or Exchange session."""

    def __init__(self, base_dir: Path, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run, *, timeout: int = 30):
        self.credentials = CredentialResolver(base_dir)
        self.runner = runner
        self.timeout = min(max(int(timeout), 1), 45)

    def collect(self, *, prefix: str, target: str, operation: str, exchange_endpoint: str = "") -> dict[str, Any]:
        try:
            username, password = self.credentials.resolve_pair(username_key=f"{prefix}_USERNAME", password_key=f"{prefix}_PASSWORD")
        except ValueError:
            return {"status": "CREDENTIAL_NOT_CONFIGURED", "connection_attempted": False, "output": None}
        target = target.replace("'", "''")
        operation_b64 = base64.b64encode(operation.encode("utf-16le")).decode("ascii")
        if exchange_endpoint:
            uri = f"http://{target}{exchange_endpoint}".replace("'", "''")
            session = (
                f"$session=New-PSSession -ConfigurationName Microsoft.Exchange -ConnectionUri '{uri}' -Credential $credential -Authentication Kerberos;"
                "$module=Import-PSSession $session -DisableNameChecking -AllowClobber;"
            )
            invocation = "& $operation"
        else:
            session = f"$session=New-PSSession -ComputerName '{target}' -Credential $credential -Authentication Negotiate;"
            invocation = "Invoke-Command -Session $session -ScriptBlock $operation"
        script = (
            "$ErrorActionPreference='Stop';$session=$null;try {"
            "$secure=ConvertTo-SecureString $env:MNE_TRANSPORT_PASSWORD -AsPlainText -Force;"
            "$credential=New-Object System.Management.Automation.PSCredential($env:MNE_TRANSPORT_USERNAME,$secure);"
            + session
            + f"$operation=[ScriptBlock]::Create([Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('{operation_b64}')));"
            + invocation
            + "} catch {exit 23} finally {if($module){Remove-Module $module -Force};if($session){Remove-PSSession $session}}"
        )
        environment = os.environ.copy()
        environment["MNE_TRANSPORT_USERNAME"] = username
        environment["MNE_TRANSPORT_PASSWORD"] = password
        try:
            process = self.runner(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", "-"], input=script, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=self.timeout, env=environment, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except subprocess.TimeoutExpired:
            return {"status": "TIMEOUT", "connection_attempted": True, "output": None}
        except OSError:
            return {"status": "TRANSPORT_EXCEPTION", "connection_attempted": True, "output": None}
        if process.returncode != 0:
            return {"status": "POWERSHELL_REMOTING_FAILED", "connection_attempted": True, "output": None}
        return {"status": "SUCCESS", "connection_attempted": True, "output": process.stdout or ""}
