"""OpenAI Responses API adapter with local thread state and `store: false`."""

from __future__ import annotations

import json
from typing import Any, Iterable

from core.llm.contracts import ProviderEvent, ProviderRequest
from .base import BaseProvider, ProviderFailure


class OpenAIProvider(BaseProvider):
    def build_payload(self, request: ProviderRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.model_id,
            "input": request.messages,
            "stream": True,
            "store": False,
            "max_output_tokens": request.max_output_tokens,
        }
        if request.tools:
            payload["tools"] = [
                {"type": "function", "name": tool["name"], "description": tool["description"], "parameters": tool["input_schema"], "strict": True}
                for tool in request.tools
            ]
        return payload

    def stream(self, request: ProviderRequest, *, credential: str | None = None) -> Iterable[ProviderEvent]:
        if not credential:
            yield self.failed("CREDENTIAL_NOT_CONFIGURED")
            return
        headers = {"Authorization": f"Bearer {credential}", "Content-Type": "application/json", "Accept": "text/event-stream"}
        tool_parts: dict[str, dict[str, Any]] = {}
        emitted: set[str] = set()
        try:
            for event in self.transport("POST", self.profile["base_url"].rstrip("/") + "/responses", headers, self.build_payload(request), request.timeout_seconds):
                self.checkpoint(request)
                etype = event.get("type")
                if etype == "response.output_text.delta":
                    yield ProviderEvent("text_delta", {"text": str(event.get("delta", ""))})
                elif etype == "response.output_item.added":
                    item = event.get("item", {})
                    if item.get("type") in {"function_call", "tool_call"}:
                        key = str(item.get("id", event.get("item_id", event.get("output_index", 0))))
                        tool_parts[key] = {"name": item.get("name"), "arguments": item.get("arguments"), "fragments": [], "provider_call_id": item.get("call_id", item.get("id"))}
                elif etype == "response.function_call_arguments.delta":
                    key = str(event.get("item_id", event.get("output_index", 0)))
                    tool_parts.setdefault(key, {"name": event.get("name"), "arguments": None, "fragments": [], "provider_call_id": event.get("call_id", event.get("item_id"))})["fragments"].append(str(event.get("delta", "")))
                elif etype == "response.function_call_arguments.done":
                    key = str(event.get("item_id", event.get("output_index", 0)))
                    part = tool_parts.setdefault(key, {"name": event.get("name"), "arguments": None, "fragments": [], "provider_call_id": event.get("call_id", event.get("item_id"))})
                    part["arguments"] = event.get("arguments") or "".join(part["fragments"]) or "{}"
                    if part.get("name"):
                        try:
                            arguments = json.loads(part["arguments"]) if isinstance(part["arguments"], str) else part["arguments"]
                        except json.JSONDecodeError:
                            yield self.failed("INVALID_TOOL_ARGUMENTS")
                            continue
                        yield ProviderEvent("tool_proposal", {"name": part["name"], "arguments": arguments, "provider_call_id": part["provider_call_id"]})
                        emitted.add(key)
                elif etype == "response.output_item.done":
                    item = event.get("item", event)
                    if item.get("type") in {"function_call", "tool_call"}:
                        key = str(item.get("id", event.get("item_id", event.get("output_index", 0))))
                        if key not in emitted:
                            part = tool_parts.get(key, {})
                            raw_arguments = item.get("arguments", part.get("arguments", "{}"))
                            try:
                                arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
                            except json.JSONDecodeError:
                                yield self.failed("INVALID_TOOL_ARGUMENTS")
                                continue
                            yield ProviderEvent("tool_proposal", {"name": item.get("name", part.get("name")), "arguments": arguments or {}, "provider_call_id": item.get("call_id", part.get("provider_call_id", item.get("id")))})
                            emitted.add(key)
                elif etype == "response.completed":
                    response = event.get("response", {})
                    yield ProviderEvent("usage", response.get("usage", {}))
                    yield ProviderEvent("completed", {"finish_reason": response.get("status", "completed")})
                elif etype == "response.failed":
                    yield self.failed("PROVIDER_RESPONSE_FAILED")
        except ProviderFailure as exc:
            yield self.failed(exc.code)
