"""Offline deterministic provider used by default and in safety validation."""

from __future__ import annotations

import re
from typing import Iterable

from core.llm.contracts import ProviderEvent, ProviderRequest
from .base import BaseProvider


class DeterministicLocalProvider(BaseProvider):
    _SECRET = re.compile(r"(?i)(password|passwd|token|secret|api[_-]?key|authorization)\s*[:=]\s*\S+")

    def stream(self, request: ProviderRequest, *, credential: str | None = None) -> Iterable[ProviderEvent]:
        prompt = next((str(item.get("content", "")) for item in reversed(request.messages) if item.get("role") == "user"), "")
        prompt = self._SECRET.sub(r"\1=[REDACTED]", prompt)
        answer = "Local deterministic mode: " + (prompt.strip() or "No user question was supplied.")
        for index in range(0, len(answer), 32):
            yield ProviderEvent("text_delta", {"text": answer[index:index + 32]})
        yield ProviderEvent("usage", {"input_tokens": max(1, len(prompt) // 4), "output_tokens": max(1, len(answer) // 4), "cost_usd": 0})
        yield ProviderEvent("completed", {"finish_reason": "stop"})

