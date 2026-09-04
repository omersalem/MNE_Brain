"""P11 provider gateway translating all adapters into canonical events."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable

from core.credentials import CredentialStore
from core.llm.contracts import ProviderEvent, ProviderRequest
from core.llm.providers import AnthropicProvider, DeterministicLocalProvider, OllamaProvider, OpenAICompatibleProvider, OpenAIProvider
from core.llm.providers.base import BaseProvider
from core.llm.registry import ProviderRegistry


class ProviderGatewayError(ValueError):
    pass


class ProviderGateway:
    ADAPTERS = {
        "deterministic_local": DeterministicLocalProvider,
        "ollama": OllamaProvider,
        "openai_compatible": OpenAICompatibleProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }

    def __init__(self, base_dir: Path, *, registry: ProviderRegistry | None = None, credentials: CredentialStore | None = None, transports: dict[str, Any] | None = None, external_calls_enabled: bool = False):
        self.base_dir = base_dir.resolve()
        self.registry = registry or ProviderRegistry(self.base_dir)
        self.credentials = credentials or CredentialStore(self.base_dir)
        self.transports = transports or {}
        self.external_calls_enabled = external_calls_enabled

    def stream(self, provider_id: str, messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None, cancellation_check: Callable[[], None] | None = None) -> Iterable[ProviderEvent]:
        profile = self.registry.get(provider_id)
        if profile["classification"] == "EXTERNAL" and not self.external_calls_enabled:
            yield BaseProvider.failed("EXTERNAL_CALLS_DISABLED")
            return
        adapter_class = self.ADAPTERS[profile["provider_type"]]
        adapter = adapter_class(profile, transport=self.transports.get(profile["provider_type"]))
        credential = self.credentials.get(profile["credential_ref"]) if profile.get("credential_ref") else None
        request = ProviderRequest(
            provider_id=provider_id,
            model_id=profile["model_id"],
            messages=messages,
            tools=tools or [],
            max_output_tokens=profile["limits"]["output_tokens"],
            timeout_seconds=profile["limits"]["timeout_seconds"],
            cancellation_check=cancellation_check,
        )
        yield from adapter.stream(request, credential=credential)
