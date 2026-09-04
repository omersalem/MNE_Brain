"""Compact context without changing evidence truth or leaking hidden state."""

from __future__ import annotations

from typing import Any


class ContextBuilder:
    def __init__(self, *, max_chars: int = 24000, recent_messages: int = 12):
        self.max_chars = max_chars
        self.recent_messages = recent_messages

    def build(self, messages: list[dict[str, Any]], evidence: list[dict[str, Any]] | None = None) -> tuple[list[dict[str, str]], dict[str, Any]]:
        recent = messages[-self.recent_messages:]
        older = messages[:-self.recent_messages]
        result: list[dict[str, str]] = []
        summary = None
        if older:
            facts = []
            for item in older:
                refs = ",".join(item.get("evidence_refs", [])) or "none"
                facts.append(f"{item.get('role')}: {item.get('content', '')[:240]} [evidence_refs={refs}]")
            summary = "Prior user-visible conversation summary; evidence status unchanged:\n" + "\n".join(facts[-20:])
            result.append({"role": "system", "content": summary})
        for item in recent:
            role = item.get("role") if item.get("role") in {"user", "assistant"} else "system"
            result.append({"role": role, "content": str(item.get("content", ""))})
        if evidence:
            compact = []
            for item in evidence:
                compact.append({"evidence_id": item.get("evidence_id"), "source": item.get("source"), "status": item.get("evidence_status", item.get("status")), "observed_at": item.get("observed_at"), "facts": item.get("facts", {})})
            result.append({"role": "system", "content": "Attributable evidence (status must not be upgraded): " + str(compact)[:8000]})
        while sum(len(item["content"]) for item in result) > self.max_chars and len(result) > 1:
            result.pop(0)
        return result, {"summarized_message_count": len(older), "summary": summary, "evidence_count": len(evidence or [])}
