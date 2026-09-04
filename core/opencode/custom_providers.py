"""Validated non-secret custom OpenCode provider metadata."""

from __future__ import annotations

import ipaddress
import json
import re
import socket
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


class CustomProviderError(ValueError):
    pass


_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
_MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,159}$")
_ENV = re.compile(r"^[A-Z][A-Z0-9_]{2,80}$")
_HEADER = re.compile(r"^[A-Za-z][A-Za-z0-9-]{0,63}$")
_SENSITIVE_HEADER = re.compile(r"auth|cookie|token|secret|password|api[-_]?key|credential", re.I)


def _public_addresses(host: str, port: int) -> list[str]:
    try:
        values = {item[4][0] for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise CustomProviderError("Provider hostname could not be resolved.") from exc
    if not values:
        raise CustomProviderError("Provider hostname returned no addresses.")
    for value in values:
        address = ipaddress.ip_address(value)
        if not address.is_global:
            raise CustomProviderError("Public provider host resolved to a private, reserved, link-local, or metadata address.")
    return sorted(values)


def validate_endpoint(raw: str, *, allow_loopback: bool = False) -> dict[str, Any]:
    try:
        parsed = urlsplit(raw)
    except ValueError as exc:
        raise CustomProviderError("Provider URL is invalid.") from exc
    if parsed.username or parsed.password:
        raise CustomProviderError("Credential-bearing provider URLs are forbidden.")
    if parsed.query or parsed.fragment:
        raise CustomProviderError("Provider URLs cannot contain query strings or fragments.")
    if not parsed.hostname or parsed.scheme not in {"https", "http"}:
        raise CustomProviderError("Only HTTPS provider URLs are accepted.")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        address = None
    is_loopback = bool(address and address.is_loopback) or parsed.hostname.casefold() == "localhost"
    if is_loopback:
        if not allow_loopback:
            raise CustomProviderError("Loopback providers require explicit local-model approval.")
        if parsed.scheme not in {"http", "https"}:
            raise CustomProviderError("Loopback provider scheme is invalid.")
        resolved = [str(address)] if address else [item[4][0] for item in socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)]
        if any(not ipaddress.ip_address(value).is_loopback for value in resolved):
            raise CustomProviderError("Loopback provider resolution changed to a non-loopback address.")
    else:
        if parsed.scheme != "https":
            raise CustomProviderError("Non-loopback providers must use HTTPS.")
        if address is not None:
            if not address.is_global:
                raise CustomProviderError("Private, reserved, link-local, and metadata provider addresses are forbidden.")
            resolved = [str(address)]
        else:
            resolved = _public_addresses(parsed.hostname, port)
    normalized = parsed.geturl().rstrip("/")
    return {"url": normalized, "resolved_addresses": resolved, "loopback": is_loopback}


class CustomProviderStore:
    """Stores metadata only; API keys are sent directly to OpenCode."""

    def __init__(self, base_dir: Path):
        self.path = base_dir / "config/opencode_custom_providers.json"
        self._lock = threading.RLock()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "providers": []}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CustomProviderError("Custom provider metadata is invalid.") from exc
        if not isinstance(value, dict) or value.get("version") != 1 or not isinstance(value.get("providers"), list):
            raise CustomProviderError("Custom provider metadata envelope is invalid.")
        return value

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return deepcopy(self._load()["providers"])

    @staticmethod
    def validate(profile: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(profile, dict):
            raise CustomProviderError("Custom provider must be an object.")
        allowed = {"provider_id", "display_name", "base_url", "protocol", "models", "environment_ref", "headers", "allow_loopback"}
        if set(profile).difference(allowed):
            raise CustomProviderError("Unknown custom provider fields were rejected.")
        provider_id = str(profile.get("provider_id", ""))
        if not _IDENTIFIER.fullmatch(provider_id):
            raise CustomProviderError("Provider ID must be a lowercase safe identifier.")
        display_name = str(profile.get("display_name", "")).strip()
        if not 1 <= len(display_name) <= 100:
            raise CustomProviderError("Provider display name is invalid.")
        protocol = str(profile.get("protocol", ""))
        if protocol not in {"chat_completions", "responses"}:
            raise CustomProviderError("Provider protocol must be Chat Completions or Responses API.")
        endpoint = validate_endpoint(str(profile.get("base_url", "")), allow_loopback=profile.get("allow_loopback") is True)
        environment_ref = profile.get("environment_ref")
        if environment_ref is not None and not _ENV.fullmatch(str(environment_ref)):
            raise CustomProviderError("Environment credential reference is invalid.")
        headers = profile.get("headers") or {}
        if not isinstance(headers, dict) or len(headers) > 20:
            raise CustomProviderError("Safe headers must be a bounded object.")
        safe_headers: dict[str, str] = {}
        for name, value in headers.items():
            if not _HEADER.fullmatch(str(name)) or _SENSITIVE_HEADER.search(str(name)):
                raise CustomProviderError("Sensitive or invalid custom headers are forbidden.")
            text = str(value)
            if not text or len(text) > 500 or "\r" in text or "\n" in text:
                raise CustomProviderError("Custom header value is invalid.")
            safe_headers[str(name)] = text
        models = profile.get("models")
        if not isinstance(models, list) or not 1 <= len(models) <= 100:
            raise CustomProviderError("At least one bounded custom model is required.")
        clean_models: list[dict[str, Any]] = []
        seen: set[str] = set()
        for model in models:
            if not isinstance(model, dict) or set(model).difference({"model_id", "display_name", "context_limit", "output_limit"}):
                raise CustomProviderError("Custom model metadata is invalid.")
            model_id = str(model.get("model_id", ""))
            name = str(model.get("display_name", "")).strip()
            if not _MODEL.fullmatch(model_id) or model_id in seen or not 1 <= len(name) <= 120:
                raise CustomProviderError("Custom model ID or display name is invalid.")
            seen.add(model_id)
            clean = {"model_id": model_id, "display_name": name}
            for key in ("context_limit", "output_limit"):
                if model.get(key) is not None:
                    value = model[key]
                    if not isinstance(value, int) or not 1 <= value <= 10_000_000:
                        raise CustomProviderError("Custom model limits are invalid.")
                    clean[key] = value
            clean_models.append(clean)
        return {
            "provider_id": provider_id,
            "display_name": display_name,
            "base_url": endpoint["url"],
            "protocol": protocol,
            "models": clean_models,
            "environment_ref": str(environment_ref) if environment_ref else None,
            "headers": safe_headers,
            "allow_loopback": endpoint["loopback"],
            "resolved_addresses": endpoint["resolved_addresses"],
        }

    def upsert(self, profile: dict[str, Any]) -> dict[str, Any]:
        clean = self.validate(profile)
        with self._lock:
            value = self._load()
            value["providers"] = [item for item in value["providers"] if item.get("provider_id") != clean["provider_id"]]
            value["providers"].append(clean)
            serialized = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
            self.path.write_text(serialized, encoding="utf-8")
        return deepcopy(clean)

    def remove(self, provider_id: str) -> bool:
        if not _IDENTIFIER.fullmatch(provider_id):
            raise CustomProviderError("Provider ID is invalid.")
        with self._lock:
            value = self._load()
            retained = [item for item in value["providers"] if item.get("provider_id") != provider_id]
            changed = len(retained) != len(value["providers"])
            if changed:
                value["providers"] = retained
                self.path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
            return changed

    def opencode_config(self) -> dict[str, Any]:
        configured: dict[str, Any] = {}
        for item in self.list():
            validate_endpoint(item["base_url"], allow_loopback=item.get("allow_loopback") is True)
            options: dict[str, Any] = {"baseURL": item["base_url"]}
            if item.get("environment_ref"):
                options["apiKey"] = "{env:" + item["environment_ref"] + "}"
            if item.get("headers"):
                options["headers"] = item["headers"]
            models: dict[str, Any] = {}
            for model in item["models"]:
                value: dict[str, Any] = {"name": model["display_name"]}
                limits = {}
                if model.get("context_limit"):
                    limits["context"] = model["context_limit"]
                if model.get("output_limit"):
                    limits["output"] = model["output_limit"]
                if limits:
                    value["limit"] = limits
                models[model["model_id"]] = value
            configured[item["provider_id"]] = {
                "npm": "@ai-sdk/openai-compatible" if item["protocol"] == "chat_completions" else "@ai-sdk/openai",
                "name": item["display_name"],
                "options": options,
                "models": models,
            }
        return configured
