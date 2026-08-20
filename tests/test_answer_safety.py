#!/usr/bin/env python3
"""Offline checks for evidence-bounded answers and live-verification gating."""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.llm.llm_adapter import LLMAdapter
from core.policy.policy_engine import PolicyEngine
from core.verification.live_verify import LiveVerificationEngine


def test_insufficient_evidence_never_reports_operational_status() -> None:
    evidence_pack = {
        "question": "What is the current firewall status?",
        "sources": [],
        "evidence_blocks": [],
        "unknowns": ["fw-example-01 is unverified; it cannot support an operational conclusion."],
    }
    result = LLMAdapter(provider="local_fallback", base_dir=base_dir).generate_response(
        evidence_pack["question"], evidence_pack
    )
    assert result["status"] == "SUCCESS"
    assert result["evidence_status"] == "INSUFFICIENT_EVIDENCE"
    assert "No operational conclusion can be made" in result["response_text"]
    assert "No remediation is permitted" in result["response_text"]


def test_live_verification_is_denied_without_policy_authorization() -> None:
    policy = PolicyEngine(base_dir=base_dir).evaluate_verification_necessity(
        "troubleshoot", has_current_live_evidence=False
    )
    assert policy["live_verification_required"] is True
    assert policy["live_verification_allowed"] is False

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        result = LiveVerificationEngine(base_dir=root).execute_live_verification("fortigate")
        assert result["status"] == "NOT_RUN"
        assert result["trust_level"] == 0
        assert not (root / "operations").exists()


if __name__ == "__main__":
    test_insufficient_evidence_never_reports_operational_status()
    test_live_verification_is_denied_without_policy_authorization()
    print("Answer safety test passed.")
