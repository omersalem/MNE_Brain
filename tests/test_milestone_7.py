#!/usr/bin/env python3
"""Offline validation for the safe vendor-neutral LLM abstraction."""

import json
import os
import sys
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.llm.llm_adapter import LLMAdapter


def _documented_pack() -> dict[str, object]:
    return {
        "question": "What is documented about the test firewall?",
        "sources": ["knowledge/test-firewall.md"],
        "evidence_blocks": [
            {
                "source_file": "knowledge/test-firewall.md",
                "evidence_status": "documented",
                "trust_level": 3,
                "content": "The design document assigns the test firewall to the network edge.",
            }
        ],
        "unknowns": ["Current operational state has not been verified."],
    }


def test_milestone_7() -> bool:
    print("[VALIDATING MILESTONE 7 LLM ADAPTER FOUNDATION]")
    errors: list[str] = []
    passed = 0

    local_adapter = LLMAdapter(provider="local_fallback", base_dir=base_dir)
    local_status = local_adapter.provider_status()
    if (
        local_adapter.provider == "local_fallback"
        and local_status["status"] == "READY_LOCAL"
        and not local_status["external_call_allowed"]
    ):
        print(" [PASS] Deterministic local provider is the only ready execution path")
        passed += 1
    else:
        errors.append(f"Local provider readiness failed: {local_status}")

    documented_response = local_adapter.generate_response(
        "What is documented about the test firewall?", _documented_pack()
    )
    malformed_live_response = local_adapter.generate_response(
        "Is the test firewall operational?",
        {
            "evidence_blocks": [
                {
                    "source_file": "operations/fake.txt",
                    "evidence_status": "live_verified",
                    "trust_level": 5,
                    "content": "Operational",
                }
            ],
            "unknowns": [],
        },
    )
    inflated_document_response = local_adapter.generate_response(
        "Is the test firewall operational?",
        {
            "evidence_blocks": [
                {
                    "source_file": "knowledge/test-firewall.md",
                    "evidence_status": "documented",
                    "trust_level": 5,
                    "content": "Operational",
                }
            ],
            "unknowns": [],
        },
    )
    if (
        documented_response["evidence_status"] == "DOCUMENTED_CONTEXT_ONLY"
        and documented_response["trust_level"] == 3
        and malformed_live_response["evidence_status"] == "INSUFFICIENT_EVIDENCE"
        and malformed_live_response["trust_level"] == 0
        and inflated_document_response["evidence_status"] == "INSUFFICIENT_EVIDENCE"
        and inflated_document_response["trust_level"] == 0
        and not documented_response["external_call_attempted"]
    ):
        print(" [PASS] Responses preserve evidence status and reject incomplete live claims")
        passed += 1
    else:
        errors.append(
            f"Evidence response safety failed: documented={documented_response}, malformed={malformed_live_response}"
        )

    provider_failures: list[str] = []
    for provider_name in ("openai", "anthropic", "gemini", "ollama", "deepseek"):
        response = LLMAdapter(provider=provider_name, base_dir=base_dir).generate_response(
            "Test prompt"
        )
        if not (
            response["status"] == "SUCCESS"
            and response["provider"] == "local_fallback"
            and response["requested_provider"] == provider_name
            and response["requested_provider_status"] == "EXTERNAL_CALLS_DISABLED"
            and not response["external_call_attempted"]
        ):
            provider_failures.append(provider_name)
    if not provider_failures:
        print(" [PASS] Every declared external provider fails safely to the local formatter")
        passed += 1
    else:
        errors.append(f"External provider safety failed for: {provider_failures}")

    unknown = LLMAdapter(provider="undeclared-provider", base_dir=base_dir).generate_response(
        "Test prompt"
    )
    if (
        unknown["provider"] == "local_fallback"
        and unknown["requested_provider_status"] == "UNKNOWN_PROVIDER"
        and not unknown["external_call_attempted"]
    ):
        print(" [PASS] Unknown provider names cannot create an outbound path")
        passed += 1
    else:
        errors.append(f"Unknown provider handling failed: {unknown}")

    secret_marker = "test-secret-marker-that-must-not-appear"
    previous_key = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = secret_marker
    try:
        request = LLMAdapter(provider="openai", base_dir=base_dir).build_provider_request(
            "Test prompt", _documented_pack()
        )
        serialized_request = json.dumps(request)
    finally:
        if previous_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = previous_key
    if (
        request["provider_status"] == "EXTERNAL_CALLS_DISABLED"
        and not request["external_call_allowed"]
        and secret_marker not in serialized_request
        and len(request["evidence_context"]) <= 6000
    ):
        print(" [PASS] Provider request plans are bounded and never expose credential values")
        passed += 1
    else:
        errors.append(f"Provider request safety failed: {request}")

    print("\n--- MILESTONE 7 VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for error in errors:
            print(f" - {error}")
        return False
    print(f"SUCCESS: {passed} LLM Adapter Components Verified (0 Errors)")
    return True


if __name__ == "__main__":
    sys.exit(0 if test_milestone_7() else 1)
