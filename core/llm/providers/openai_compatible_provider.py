"""Reviewed loopback OpenAI-compatible chat adapter."""

from __future__ import annotations

import json
from typing import Any, Iterable

from core.llm.contracts import ProviderEvent, ProviderRequest
from .base import BaseProvider, ProviderFailure


class OpenAICompatibleProvider(BaseProvider):
    def build_payload(self, request: ProviderRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": request.model_id, "messages": request.messages, "stream": True, "max_tokens": request.max_output_tokens}
        if request.tools:
            payload["tools"] = [
                {"type": "function", "function": {"name": tool["name"], "description": tool["description"], "parameters": tool["input_schema"]}}
                for tool in request.tools
            ]
        return payload

    def stream(self, request: ProviderRequest, *, credential: str | None = None) -> Iterable[ProviderEvent]:
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        if credential:
            headers["Authorization"] = f"Bearer {credential}"
        tool_parts: dict[str, dict[str, Any]] = {}
        try:
            for event in self.transport("POST", self.profile["base_url"].rstrip("/") + "/chat/completions", headers, self.build_payload(request), request.timeout_seconds):
                self.checkpoint(request)
                choices = event.get("choices", [])
                for choice in choices:
                    delta = choice.get("delta", {})
                    if delta.get("content"):
                        yield ProviderEvent("text_delta", {"text": str(delta["content"])})
                    for index, tool in enumerate(delta.get("tool_calls", [])):
                        function = tool.get("function", {})
                        key = str(tool.get("id") or tool.get("index", index))
                        part = tool_parts.setdefault(key, {"name": None, "argument_fragments": [], "provider_call_id": tool.get("id")})
                        if function.get("name"):
                            part["name"] = function["name"]
                        if function.get("arguments"):
                            part["argument_fragments"].append(str(function["arguments"]))
                    if choice.get("finish_reason"):
                        for part in tool_parts.values():
                            try:
                                arguments = json.loads("".join(part["argument_fragments"]) or "{}")
                            except json.JSONDecodeError:
                                yield self.failed("INVALID_TOOL_ARGUMENTS")
                                continue
                            yield ProviderEvent("tool_proposal", {"name": part["name"], "arguments": arguments, "provider_call_id": part["provider_call_id"]})
                        tool_parts.clear()
                        yield ProviderEvent("completed", {"finish_reason": choice["finish_reason"]})
                if event.get("usage"):
                    yield ProviderEvent("usage", event["usage"])
        except ProviderFailure as exc:
            yield self.failed(exc.code)
