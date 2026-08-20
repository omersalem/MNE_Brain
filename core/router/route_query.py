#!/usr/bin/env python3
"""Deterministic query routing with bounded entity disambiguation."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.entity.build_entity_index import EntityIndexBuilder


class QueryRouter:
    """Classify questions without using an LLM or invoking live verification."""

    ASSET_KEYWORDS = [
        r"fw-", r"sw-", r"router", r"firewall", r"switch", r"cisco", r"vc-", r"vcenter",
        r"dc-", r"domain controller", r"active directory", r"\bdns\b", r"exch-", r"exchange",
        r"mail", r"\bf5\b", r"big-ip", r"waf", r"san-", r"storage", r"backup", r"veeam",
        r"esxi", r"vmware", r"branch", r"\b172\.", r"\b10\.", r"\b192\.168\.",
    ]
    TROUBLESHOOT_KEYWORDS = [
        r"down", r"slow", r"fail", r"fault", r"issue", r"error", r"packet loss",
        r"cannot connect", r"unreachable", r"unavailable", r"timeout", r"degraded",
        r"authentication", r"cannot login", r"outage", r"troubleshoot", r"remediate",
    ]
    ASSET_INTENT_KEYWORDS = [
        r"\bstatus\b", r"\bhealth\b", r"\bcheck\b", r"\bwhere\b", r"\bpolicy\b", r"\blookup\b",
    ]

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or PROJECT_ROOT
        self.entity_builder = EntityIndexBuilder(base_dir=self.base_dir)

    @staticmethod
    def _candidate_options(candidates: list[dict[str, Any]]) -> list[dict[str, str | int]]:
        return [
            {
                "option_number": number,
                "entity_id": candidate["entity_id"],
                "name": candidate["name"],
                "category": candidate["category"],
            }
            for number, candidate in enumerate(candidates[:3], start=1)
        ]

    def generate_disambiguation_request(
        self, candidates: list[dict[str, Any]], reason: str
    ) -> dict[str, Any]:
        options = self._candidate_options(candidates)
        if options:
            prompt = "More than one known target matches this request. Select the intended entity."
        else:
            prompt = "No known target was resolved. Provide a hostname, IP address, service, or branch."
        return {
            "requires_clarification": True,
            "reason": reason,
            "prompt": prompt,
            "options": options,
        }

    def classify_query(self, question: str) -> dict[str, Any]:
        q_lower = question.casefold()
        is_troubleshoot = any(re.search(keyword, q_lower) for keyword in self.TROUBLESHOOT_KEYWORDS)
        detected_patterns = [keyword for keyword in self.ASSET_KEYWORDS if re.search(keyword, q_lower)]
        has_asset_intent = any(re.search(keyword, q_lower) for keyword in self.ASSET_INTENT_KEYWORDS)
        should_resolve = is_troubleshoot or bool(detected_patterns) or has_asset_intent
        candidates = self.entity_builder.resolve_entity(question) if should_resolve else []
        has_asset = bool(detected_patterns or candidates or has_asset_intent)

        if is_troubleshoot:
            route_type = "troubleshoot"
            task_target = "tasks/investigate.md"
            requires_entity_resolution = True
        elif has_asset:
            route_type = "asset"
            task_target = "tasks/verify-live.md"
            requires_entity_resolution = True
        else:
            route_type = "concept"
            task_target = "tasks/discover-network.md"
            requires_entity_resolution = False

        clarification_request = None
        if requires_entity_resolution and not candidates:
            clarification_request = self.generate_disambiguation_request(
                [], "No canonical entity matched the target in the question."
            )
            resolution_status = "unknown"
        elif len(candidates) > 1:
            clarification_request = self.generate_disambiguation_request(
                candidates, "Multiple canonical entities matched the target."
            )
            resolution_status = "ambiguous"
        elif candidates:
            resolution_status = "exact"
        else:
            resolution_status = "not_required"

        return {
            "question": question,
            "route_type": route_type,
            "has_asset": has_asset,
            "detected_asset_patterns": detected_patterns,
            "requires_entity_resolution": requires_entity_resolution,
            "resolution_status": resolution_status,
            "resolved_entity_ids": [candidate["entity_id"] for candidate in candidates[:3]],
            "task_target": task_target,
            "template_format": "dynamic_evidence_answer",
            "clarification_request": clarification_request,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Route an MNE Brain question deterministically")
    parser.add_argument("--question", required=True, help="Question to classify")
    args = parser.parse_args()
    print(json.dumps(QueryRouter().classify_query(args.question), indent=2))
