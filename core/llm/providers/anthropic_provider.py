"""Anthropic Messages streaming adapter."""

from __future__ import annotations

import json
from typing import Any, Iterable

from core.llm.contracts import ProviderEvent, ProviderRequest
from .base import BaseProvider, ProviderFailure


class AnthropicProvider(BaseProvider):
    def build_payload(self, request: ProviderRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": request.model_id, "messages": request.messages, "max_tokens": request.max_output_tokens, "stream": True}
        if request.tools:
            payload["tools"] = request.tools
        return payload

    def stream(self, request: ProviderRequest, *, credential: str | None = None) -> Iterable[ProviderEvent]:
        if not credential:
            yield self.failed("CREDENTIAL_NOT_CONFIGURED")
            return
        headers = {"x-api-key": credential, "anthropic-version": "2023-06-01", "content-type": "application/json", "accept": "text/event-stream"}
        tool_parts: dict[str, dict[str, Any]] = {}
        try:
            for event in self.transport("POST", self.profile["base_url"].rstrip("/") + "/messages", headers, self.build_payload(request), request.timeout_seconds):
                self.checkpoint(request)
                etype = event.get("type")
                if etype == "content_block_start" and event.get("content_block", {}).get("type") == "tool_use":
                    block = event["content_block"]
                    tool_parts[str(event.get("index", 0))] = {"name": block.get("name"), "arguments": block.get("input", {}), "provider_call_id": block.get("id")}
                elif etype == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        yield ProviderEvent("text_delta", {"text": str(delta.get("text", ""))})
                    elif delta.get("type") == "input_json_delta":
                        tool_parts.setdefault(str(event.get("index", 0)), {}).setdefault("argument_fragments", []).append(str(delta.get("partial_json", "")))
                elif etype == "content_block_stop":
                    proposal = tool_parts.pop(str(event.get("index", 0)), None)
                    if proposal:
                        fragments = proposal.pop("argument_fragments", [])
                        if fragments:
                            try:
                                proposal["arguments"] = json.loads("".join(fragments))
                            except json.JSONDecodeError:
                                yield self.failed("INVALID_TOOL_ARGUMENTS")
                                continue
                        yield ProviderEvent("tool_proposal", proposal)
                elif etype == "message_delta" and event.get("usage"):
                    yield ProviderEvent("usage", event["usage"])
                elif etype == "message_stop":
                    yield ProviderEvent("completed", {"finish_reason": "stop"})
                elif etype == "error":
                    yield self.failed("PROVIDER_RESPONSE_FAILED")
        except ProviderFailure as exc:
            yield self.failed(exc.code)
