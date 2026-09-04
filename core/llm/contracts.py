"""Canonical P11 provider request and event contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Protocol


CANONICAL_PROVIDER_EVENTS = {"text_delta", "tool_proposal", "usage", "completed", "failed"}


@dataclass(frozen=True)
class ProviderRequest:
    provider_id: str
    model_id: str
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] = field(default_factory=list)
    max_output_tokens: int = 2048
    timeout_seconds: int = 60
    cancellation_check: Callable[[], None] | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class ProviderEvent:
    event_type: str
    payload: dict[str, Any]

    def __post_init__(self) -> None:
        if self.event_type not in CANONICAL_PROVIDER_EVENTS:
            raise ValueError(f"Unsupported canonical provider event: {self.event_type}")


class ProviderAdapter(Protocol):
    def stream(self, request: ProviderRequest, *, credential: str | None = None) -> Iterable[ProviderEvent]: ...
