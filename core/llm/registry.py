"""Schema-governed, refreshable P11 provider profile registry."""

from __future__ import annotations

import ipaddress
import json
import socket
import urllib.parse
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any

import jsonschema
import yaml


class ProviderRegistryError(ValueError):
    pass


class ProviderRegistry:
    EXTERNAL_ORIGINS = {
        "openai": ("https", "api.openai.com", 443, "/v1"),
        "anthropic": ("https", "api.anthropic.com", 443, "/v1"),
    }

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()
        self.catalog_path = self.base_dir / "config/provider_catalog.yaml"
        self._lock = RLock()
        self._profiles: dict[str, dict[str, Any]] = {}
        self.reload()

    @staticmethod
    def _is_loopback_host(host: str | None) -> bool:
        if not host:
            return False
        if host.lower() == "localhost":
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    @classmethod
    def validate_base_url(cls, profile: dict[str, Any]) -> None:
        parsed = urllib.parse.urlsplit(profile["base_url"])
        ptype = profile["provider_type"]
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ProviderRegistryError("Provider base URL cannot contain credentials, query, or fragment.")
        if ptype in {"codex_app_server", "antigravity_cli"}:
            expected = "codex-app-server" if ptype == "codex_app_server" else "antigravity-cli"
            if parsed.scheme != "stdio" or parsed.netloc != expected or parsed.path.rstrip("/"):
                raise ProviderRegistryError(f"{ptype} provider must use stdio://{expected}.")
            if profile["classification"] != "LOCAL" or profile.get("credential_ref") is not None:
                raise ProviderRegistryError("Local agent engines use cached interactive sign-in and no repository credential reference.")
            return
        if ptype == "opencode":
            if parsed.scheme != "http" or not cls._is_loopback_host(parsed.hostname):
                raise ProviderRegistryError("OpenCode provider must use a loopback HTTP server URL.")
            if profile["classification"] != "LOCAL" or profile.get("credential_ref") is not None:
                raise ProviderRegistryError("OpenCode engine credentials are managed by OpenCode, not the MNE provider registry.")
            return
        if ptype == "deterministic_local":
            if parsed.scheme != "local" or parsed.netloc != "deterministic":
                raise ProviderRegistryError("Deterministic provider must use local://deterministic.")
            return
        if profile["classification"] == "LOCAL":
            if parsed.scheme != "http" or not cls._is_loopback_host(parsed.hostname) or parsed.path.rstrip("/") not in {"", "/v1"}:
                raise ProviderRegistryError("Local provider base URL must be loopback HTTP.")
            return
        expected = cls.EXTERNAL_ORIGINS.get(ptype)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if expected is None or (parsed.scheme, parsed.hostname, port, parsed.path.rstrip("/")) != expected:
            raise ProviderRegistryError("External provider base URL is not an approved HTTPS origin.")
        try:
            candidate = ipaddress.ip_address(parsed.hostname or "")
            if candidate.is_private or candidate.is_loopback or candidate.is_link_local or candidate.is_multicast:
                raise ProviderRegistryError("External provider URL resolved to a prohibited address.")
        except ValueError:
            pass

    def reload(self) -> None:
        data = yaml.safe_load(self.catalog_path.read_text(encoding="utf-8")) or {}
        if set(data) != {"catalog_version", "refresh_policy", "profiles"} or data.get("refresh_policy") != "MANUAL_REVIEW_REQUIRED":
            raise ProviderRegistryError("Provider catalog envelope is invalid.")
        schema_dir = self.base_dir / "00_meta/schemas"
        profile_schema = json.loads((schema_dir / "provider-profile.schema.json").read_text(encoding="utf-8"))
        capability_schema = json.loads((schema_dir / "provider-capabilities.schema.json").read_text(encoding="utf-8"))
        profile_schema["properties"]["capabilities"] = capability_schema
        profiles: dict[str, dict[str, Any]] = {}
        for profile in data.get("profiles", []):
            jsonschema.Draft7Validator(profile_schema, format_checker=jsonschema.FormatChecker()).validate(profile)
            self.validate_base_url(profile)
            if profile["provider_id"] in profiles:
                raise ProviderRegistryError("Duplicate provider ID.")
            profiles[profile["provider_id"]] = deepcopy(profile)
        if "prv_local_deterministic" not in profiles or not profiles["prv_local_deterministic"]["enabled"]:
            raise ProviderRegistryError("Enabled deterministic local fallback is mandatory.")
        with self._lock:
            self._profiles = profiles

    def validate_profile(self, profile: dict[str, Any]) -> None:
        schema_dir = self.base_dir / "00_meta/schemas"
        profile_schema = json.loads((schema_dir / "provider-profile.schema.json").read_text(encoding="utf-8"))
        capability_schema = json.loads((schema_dir / "provider-capabilities.schema.json").read_text(encoding="utf-8"))
        profile_schema["properties"]["capabilities"] = capability_schema
        jsonschema.Draft7Validator(profile_schema, format_checker=jsonschema.FormatChecker()).validate(profile)
        self.validate_base_url(profile)

    def add_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        self.validate_profile(profile)
        with self._lock:
            if profile["provider_id"] in self._profiles:
                raise ProviderRegistryError("Provider ID already exists.")
            self._profiles[profile["provider_id"]] = deepcopy(profile)
            return deepcopy(profile)

    def list_profiles(self, *, include_disabled: bool = True) -> list[dict[str, Any]]:
        with self._lock:
            values = [deepcopy(item) for item in self._profiles.values() if include_disabled or item["enabled"]]
        for profile in values:
            profile["credential_status"] = "REFERENCE_DECLARED" if profile.get("credential_ref") else "NOT_REQUIRED"
        return values

    def get(self, provider_id: str, *, require_enabled: bool = True) -> dict[str, Any]:
        with self._lock:
            profile = deepcopy(self._profiles.get(provider_id))
        if profile is None:
            raise ProviderRegistryError("Unknown provider profile.")
        if require_enabled and not profile["enabled"]:
            raise ProviderRegistryError("Provider profile is disabled.")
        return profile

    def set_enabled(self, provider_id: str, enabled: bool) -> dict[str, Any]:
        if provider_id == "prv_local_deterministic" and not enabled:
            raise ProviderRegistryError("The deterministic fallback cannot be disabled.")
        with self._lock:
            if provider_id not in self._profiles:
                raise ProviderRegistryError("Unknown provider profile.")
            self._profiles[provider_id]["enabled"] = bool(enabled)
            return deepcopy(self._profiles[provider_id])
