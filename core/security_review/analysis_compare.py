"""
Security Analysis Comparison Engine for MNE_Brain Release 2.
Compares Codex App Server and Antigravity CLI analysis results for the same run or incident.
Organizes provider output without inventing ungrounded third conclusions.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> Set[str]:
    """Extracts normalized content words from text for semantic overlap calculation."""
    words = re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", text.lower())
    stop_words = {
        "the", "and", "for", "that", "this", "with", "from", "have", "been",
        "were", "which", "about", "into", "more", "other", "some", "such",
        "than", "then", "them", "these", "there", "their", "will", "would",
    }
    return {w for w in words if w not in stop_words}


def _similarity(tokens_a: Set[str], tokens_b: Set[str]) -> float:
    """Calculates Jaccard similarity between two token sets."""
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    return len(intersection) / len(union) if union else 0.0


class SecurityAnalysisComparator:
    """Compares and reconciles multi-engine analysis outputs."""

    def __init__(self, clock: Optional[Any] = None):
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def _generate_comparison_id(self) -> str:
        timestamp = int(time.time())
        unique = uuid.uuid4().hex[:6]
        return f"cmp-{timestamp}-{unique}"

    def compare(
        self,
        codex_result: Dict[str, Any],
        antigravity_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compares analysis results from Codex and Antigravity."""
        now_iso = self.clock().isoformat()
        target_type = "RUN"
        if codex_result.get("incident_fingerprint") or antigravity_result.get("incident_fingerprint"):
            target_type = "INCIDENT"

        run_id = codex_result.get("run_id") or antigravity_result.get("run_id")
        fingerprint = codex_result.get("incident_fingerprint") or antigravity_result.get("incident_fingerprint")

        codex_id = codex_result.get("analysis_id", "unknown-codex")
        antigravity_id = antigravity_result.get("analysis_id", "unknown-antigravity")

        codex_hypotheses: List[Dict[str, Any]] = codex_result.get("ranked_hypotheses") or codex_result.get("hypotheses", [])
        antigravity_hypotheses: List[Dict[str, Any]] = antigravity_result.get("ranked_hypotheses") or antigravity_result.get("hypotheses", [])

        common_conclusions: List[str] = []
        codex_only_conclusions: List[str] = []
        antigravity_only_conclusions: List[str] = []
        conflicting_conclusions: List[Dict[str, Any]] = []

        # Check explicit conclusions overlap
        c_explicit = codex_result.get("common_conclusions") or codex_result.get("conclusions", [])
        a_explicit = antigravity_result.get("common_conclusions") or antigravity_result.get("conclusions", [])
        for c_c in c_explicit:
            c_c_clean = str(c_c).strip().lower()
            for a_c in a_explicit:
                if str(a_c).strip().lower() == c_c_clean and c_c not in common_conclusions:
                    common_conclusions.append(c_c)

        matched_codex = set()
        matched_antigravity = set()

        # Compare hypotheses across both engines
        for c_idx, c_hypo in enumerate(codex_hypotheses):
            c_text = c_hypo.get("hypothesis", "")
            c_like = (c_hypo.get("likelihood") or "UNKNOWN").upper()
            c_tokens = _tokenize(c_text)

            best_match_idx = -1
            best_sim = 0.0

            for a_idx, a_hypo in enumerate(antigravity_hypotheses):
                if a_idx in matched_antigravity:
                    continue
                a_text = a_hypo.get("hypothesis", "")
                a_tokens = _tokenize(a_text)
                sim = _similarity(c_tokens, a_tokens)
                if sim > best_sim:
                    best_sim = sim
                    best_match_idx = a_idx

            if best_match_idx >= 0 and best_sim >= 0.25:
                # Found corresponding hypothesis
                a_hypo = antigravity_hypotheses[best_match_idx]
                a_text = a_hypo.get("hypothesis", "")
                a_like = (a_hypo.get("likelihood") or "UNKNOWN").upper()
                matched_codex.add(c_idx)
                matched_antigravity.add(best_match_idx)

                # Check for likelihood conflict
                high_vs_low = (c_like == "HIGH" and a_like in ("LOW", "UNKNOWN")) or (a_like == "HIGH" and c_like in ("LOW", "UNKNOWN"))
                if high_vs_low:
                    conflicting_conclusions.append({
                        "topic": c_text,
                        "codex_assessment": f"{c_like}: {c_hypo.get('explanation', c_text)}",
                        "antigravity_assessment": f"{a_like}: {a_hypo.get('explanation', a_text)}",
                        "conflict_reason": f"Likelihood divergence: Codex assessed {c_like} while Antigravity assessed {a_like}.",
                    })
                else:
                    common_conclusions.append(
                        f"Both engines agree: '{c_text}' (Codex likelihood: {c_like}, Antigravity likelihood: {a_like})"
                    )

        # Record unmatched hypotheses
        for c_idx, c_hypo in enumerate(codex_hypotheses):
            if c_idx not in matched_codex:
                c_text = c_hypo.get("hypothesis", "")
                c_like = (c_hypo.get("likelihood") or "UNKNOWN").upper()
                codex_only_conclusions.append(f"{c_text} (Likelihood: {c_like})")

        for a_idx, a_hypo in enumerate(antigravity_hypotheses):
            if a_idx not in matched_antigravity:
                a_text = a_hypo.get("hypothesis", "")
                a_like = (a_hypo.get("likelihood") or "UNKNOWN").upper()
                antigravity_only_conclusions.append(f"{a_text} (Likelihood: {a_like})")

        # Compare recommended diagnostics
        codex_diags = codex_result.get("recommended_diagnostics", [])
        antigravity_diags = antigravity_result.get("recommended_diagnostics", [])
        shared_diagnostics: List[str] = []

        for cd in codex_diags:
            cd_clean = cd.strip().lower()
            for ad in antigravity_diags:
                ad_clean = ad.strip().lower()
                if cd_clean in ad_clean or ad_clean in cd_clean or _similarity(_tokenize(cd_clean), _tokenize(ad_clean)) >= 0.35:
                    shared_diagnostics.append(cd)
                    break

        # Compare and compile unresolved questions (missing evidence)
        codex_missing = codex_result.get("missing_evidence") or codex_result.get("unresolved_questions", [])
        antigravity_missing = antigravity_result.get("missing_evidence") or antigravity_result.get("unresolved_questions", [])
        unresolved_questions: List[str] = []
        seen_questions = set()
        for q in codex_missing + antigravity_missing:
            q_clean = q.strip()
            if q_clean and q_clean.lower() not in seen_questions:
                seen_questions.add(q_clean.lower())
                unresolved_questions.append(q_clean)

        return {
            "comparison_id": self._generate_comparison_id(),
            "target_type": target_type,
            "run_id": run_id,
            "incident_fingerprint": fingerprint,
            "codex_analysis_id": codex_id,
            "antigravity_analysis_id": antigravity_id,
            "created_at": now_iso,
            "common_conclusions": common_conclusions,
            "codex_only_conclusions": codex_only_conclusions,
            "antigravity_only_conclusions": antigravity_only_conclusions,
            "conflicting_conclusions": conflicting_conclusions,
            "shared_diagnostics": shared_diagnostics,
            "unresolved_questions": unresolved_questions,
        }


def compare_analyses(codex_result: Dict[str, Any], antigravity_result: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience helper to compare Codex and Antigravity analysis results."""
    return SecurityAnalysisComparator().compare(codex_result, antigravity_result)
