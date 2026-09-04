"""Shared provider HTTP transport and secret-safe failure handling."""

from __future__ import annotations

import json
import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Iterable

from core.llm.contracts import ProviderEvent, ProviderRequest


SAFE_PROVIDER_ERRORS: dict[str, tuple[str, bool]] = {
    "CREDENTIAL_NOT_CONFIGURED": ("The provider credential is not configured.", False),
    "CREDENTIAL_INVALID": ("The provider rejected the configured credential.", False),
    "PROVIDER_RATE_LIMITED": ("The provider rate limit was reached. Retry later.", True),
    "PROVIDER_TIMEOUT": ("The provider did not respond before the timeout.", True),
    "PROVIDER_REQUEST_INVALID": ("The provider rejected the request or model configuration.", False),
    "PROVIDER_UNAVAILABLE": ("The provider is temporarily unavailable.", True),
    "PROVIDER_RESPONSE_INVALID": ("The provider returned an invalid streaming response.", True),
    "PROVIDER_STREAM_INCOMPLETE": ("The provider stream ended before completion.", True),
    "EXTERNAL_CALLS_DISABLED": ("External provider calls are disabled by server policy.", False),
    "TURN_ALREADY_ACTIVE": ("Wait for the active turn to finish or cancel it first.", True),
    "OWNER_CANCELLED": ("The turn was cancelled by the owner.", True),
    "TOOL_PROPOSAL_REJECTED": ("The proposed tool call did not satisfy server policy.", False),
    "TOOL_EXECUTION_FAILED": ("A governed tool failed while collecting evidence.", True),
    "TOOL_STEP_LIMIT_REACHED": ("The assistant requested too many tool steps without completing an answer.", True),
    "AUTHORIZATION_INVALID": ("The external-data authorization is missing, expired, or changed.", True),
    "CODEX_AUTH_REQUIRED": ("Codex is not signed in with ChatGPT. Run `codex login` as the GUI server user.", False),
    "CODEX_APP_SERVER_EXITED": ("The local Codex App Server stopped during the turn. It will be restarted for the next turn.", True),
    "CODEX_APP_SERVER_UNAVAILABLE": ("The local Codex App Server could not be initialized.", True),
    "CODEX_TURN_FAILED": ("The Codex agent turn failed before producing a complete answer.", True),
    "CODEX_TURN_CANCELLED": ("The Codex agent turn was cancelled by the owner.", True),
    "CODEX_EMPTY_RESPONSE": ("The Codex agent completed without returning a final answer. Retry the question.", True),
    "OPENCODE_NOT_INSTALLED": ("OpenCode is not installed for the GUI server user.", False),
    "OPENCODE_VERSION_UNSUPPORTED": ("The installed OpenCode version is unsupported.", False),
    "OPENCODE_AUTH_REQUIRED": ("The selected OpenCode provider requires authentication.", False),
    "OPENCODE_NO_CONNECTED_PROVIDER": ("Connect an OpenCode provider before starting a turn.", False),
    "OPENCODE_NO_MODELS": ("Connected OpenCode providers currently expose no models.", True),
    "OPENCODE_MODEL_REMOVED": ("The pinned OpenCode model is no longer available. Choose another model.", False),
    "OPENCODE_RATE_LIMITED": ("The selected OpenCode provider is rate limited. Retry later.", True),
    "OPENCODE_SERVER_UNAVAILABLE": ("The protected local OpenCode server is unavailable.", True),
    "OPENCODE_CONNECTION_FAILED": ("The OpenCode provider request failed safely.", True),
    "OPENCODE_TIMEOUT": ("The OpenCode turn exceeded the governed timeout.", True),
    "OPENCODE_EMPTY_RESPONSE": ("OpenCode completed without returning a final answer.", True),
    "OPENCODE_TURN_CANCELLED": ("The OpenCode turn was cancelled by the owner.", True),
}


class ProviderFailure(RuntimeError):
    def __init__(self, code: str, *, http_status: int | None = None):
        self.code = code if code in SAFE_PROVIDER_ERRORS else "PROVIDER_UNAVAILABLE"
        self.http_status = http_status
        message, self.retryable = SAFE_PROVIDER_ERRORS[self.code]
        super().__init__(message)


Transport = Callable[[str, str, dict[str, str], dict[str, Any], int], Iterable[dict[str, Any]]]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderFailure("Provider redirects are rejected by SSRF policy.")


def _validate_resolution(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname or ""
    if host.lower() == "localhost":
        return
    try:
        literal = ipaddress.ip_address(host)
        addresses = [literal]
    except ValueError:
        try:
            addresses = [ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)]
        except (OSError, ValueError) as exc:
            raise ProviderFailure("Provider host resolution failed.") from exc
    for address in addresses:
        if parsed.scheme == "http" and address.is_loopback:
            continue
        if address.is_private or address.is_loopback or address.is_link_local or address.is_multicast or address.is_reserved or address.is_unspecified:
            raise ProviderFailure("Provider host resolved to a prohibited address.")


def _http_failure(status: int) -> ProviderFailure:
    if status in {401, 403}:
        code = "CREDENTIAL_INVALID"
    elif status == 429:
        code = "PROVIDER_RATE_LIMITED"
    elif status in {408, 504}:
        code = "PROVIDER_TIMEOUT"
    elif status in {400, 404, 405, 409, 422}:
        code = "PROVIDER_REQUEST_INVALID"
    else:
        code = "PROVIDER_UNAVAILABLE"
    return ProviderFailure(code, http_status=status)


def _decode_sse_data(data_lines: list[str]) -> dict[str, Any] | None:
    data = "\n".join(data_lines).strip()
    if not data or data == "[DONE]":
        return None
    try:
        value = json.loads(data)
    except json.JSONDecodeError as exc:
        raise ProviderFailure("PROVIDER_RESPONSE_INVALID") from exc
    if not isinstance(value, dict):
        raise ProviderFailure("PROVIDER_RESPONSE_INVALID")
    return value


def urlopen_json_stream(method: str, url: str, headers: dict[str, str], payload: dict[str, Any], timeout: int) -> Iterable[dict[str, Any]]:
    _validate_resolution(url)
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:
            data_lines: list[str] = []
            for raw in response:
                line = raw.decode("utf-8", errors="strict").rstrip("\r\n")
                if not line:
                    event = _decode_sse_data(data_lines)
                    data_lines = []
                    if event is not None:
                        yield event
                    continue
                if line.startswith(":") or line.startswith(("event:", "id:", "retry:")):
                    continue
                if line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
                    continue
                if data_lines:
                    event = _decode_sse_data(data_lines)
                    data_lines = []
                    if event is not None:
                        yield event
                event = _decode_sse_data([line])
                if event is not None:
                    yield event
            event = _decode_sse_data(data_lines)
            if event is not None:
                yield event
    except urllib.error.HTTPError as exc:
        raise _http_failure(exc.code) from exc
    except (TimeoutError, socket.timeout) as exc:
        raise ProviderFailure("PROVIDER_TIMEOUT") from exc
    except UnicodeDecodeError as exc:
        raise ProviderFailure("PROVIDER_RESPONSE_INVALID") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            raise ProviderFailure("PROVIDER_TIMEOUT") from exc
        raise ProviderFailure("PROVIDER_UNAVAILABLE") from exc
    except OSError as exc:
        raise ProviderFailure("PROVIDER_UNAVAILABLE") from exc


class BaseProvider:
    def __init__(self, profile: dict[str, Any], transport: Transport | None = None):
        self.profile = profile
        self.transport = transport or urlopen_json_stream

    def stream(self, request: ProviderRequest, *, credential: str | None = None) -> Iterable[ProviderEvent]:
        raise NotImplementedError

    @staticmethod
    def failed(code: str) -> ProviderEvent:
        safe_code = code if code in SAFE_PROVIDER_ERRORS else "PROVIDER_UNAVAILABLE"
        message, retryable = SAFE_PROVIDER_ERRORS[safe_code]
        return ProviderEvent("failed", {"code": safe_code, "message": message, "retryable": retryable})

    @staticmethod
    def checkpoint(request: ProviderRequest) -> None:
        if request.cancellation_check:
            request.cancellation_check()
