#!/usr/bin/env python3
"""Deterministic answer framing that never turns missing evidence into a conclusion."""

from typing import Any


class StructuredAnswerBuilder:
    """Format evidence state for an AI or local fallback without diagnosing issues."""

    def build(self, question: str, evidence_pack: dict[str, Any]) -> dict[str, Any]:
        blocks = evidence_pack.get("evidence_blocks", [])
        unknowns = evidence_pack.get("unknowns", [])
        statuses = {block.get("evidence_status") for block in blocks}

        if not blocks:
            status = "INSUFFICIENT_EVIDENCE"
            answer = "No operational conclusion can be made from the available evidence."
            next_check = "Request an approved, target-specific read-only verification after the required security gate is authorized."
        elif statuses == {"live_verified"}:
            status = "LIVE_EVIDENCE_AVAILABLE"
            answer = "Current live evidence is available, but interpretation must remain limited to the cited checks."
            next_check = "Review the cited checks and collect only the next evidence needed to resolve remaining unknowns."
        else:
            status = "DOCUMENTED_CONTEXT_ONLY"
            answer = "Canonical documentation is available, but it does not establish current operational state."
            next_check = "Use an approved, target-specific read-only verification if current state is required."

        evidence_lines = [
            f"- `{block['source_file']}` — {block['evidence_status']} (trust level {block['trust_level']})"
            for block in blocks
        ] or ["- None"]
        unknown_lines = [f"- {item}" for item in unknowns] or ["- None recorded"]
        response_text = "\n".join(
            [
                "## MNE_Brain Evidence-Based Response",
                "",
                f"**Status:** {status}",
                f"**Answer:** {answer}",
                "",
                "### Evidence",
                *evidence_lines,
                "",
                "### Unknowns",
                *unknown_lines,
                "",
                f"**Next check:** {next_check}",
                "**Action:** No remediation is permitted from this response alone.",
            ]
        )
        return {
            "status": status,
            "response_text": response_text,
            "sources": evidence_pack.get("sources", []),
            "unknowns": unknowns,
            "trust_level": max((block.get("trust_level", 0) for block in blocks), default=0),
            "question": question,
        }
