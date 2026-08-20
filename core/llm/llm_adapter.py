#!/usr/bin/env python3
"""Vendor-neutral LLM provider planning with an offline-safe default."""

import os
from pathlib import Path
from typing import Any

import yaml

from core.answers.structured_answer import StructuredAnswerBuilder


class LLMAdapter:
    """Describe provider readiness and generate evidence-safe local responses.

    External transports are intentionally absent from this foundation. Merely
    selecting a provider or configuring an environment variable cannot trigger
    an outbound request.
    """

    LOCAL_PROVIDER = "local_fallback"

    def __init__(self, provider: str | None = None, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.config_path = self.base_dir / "config" / "llm_config.yaml"
        self.config = self._load_config()
        configured_default = self.config.get("default_provider", self.LOCAL_PROVIDER)
        requested_provider = provider or os.getenv("LLM_PROVIDER") or configured_default
        self.provider = str(requested_provider).strip().casefold() or self.LOCAL_PROVIDER

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {
                "default_provider": self.LOCAL_PROVIDER,
                "external_calls": {"enabled": False},
                "providers": {self.LOCAL_PROVIDER: {"model": "mne-brain-local-v2"}},
            }
        with self.config_path.open("r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file) or {}
        if not isinstance(config, dict):
            raise ValueError("LLM configuration must contain a mapping.")
        return config

    def provider_status(self) -> dict[str, Any]:
        """Report provider readiness without reading or exposing credential values."""
        providers = self.config.get("providers", {})
        provider_config = providers.get(self.provider)
        if self.provider == self.LOCAL_PROVIDER:
            return {
                "requested_provider": self.provider,
                "status": "READY_LOCAL",
                "model": (provider_config or {}).get("model", "mne-brain-local-v2"),
                "external_call_allowed": False,
                "credential_configured": False,
                "reason": "Deterministic local evidence formatting is available.",
            }
        if not isinstance(provider_config, dict):
            return {
                "requested_provider": self.provider,
                "status": "UNKNOWN_PROVIDER",
                "model": None,
                "external_call_allowed": False,
                "credential_configured": False,
                "reason": "The requested provider is not declared in llm_config.yaml.",
            }

        credential_env = provider_config.get("api_key_env") or provider_config.get("endpoint_env")
        credential_configured = bool(
            isinstance(credential_env, str) and credential_env and os.getenv(credential_env)
        )
        external_policy = self.config.get("external_calls", {})
        external_enabled = bool(external_policy.get("enabled", False))
        if not external_enabled:
            status = "EXTERNAL_CALLS_DISABLED"
            reason = external_policy.get(
                "reason", "External LLM calls are disabled by configuration."
            )
        elif not credential_configured:
            status = "NOT_CONFIGURED"
            reason = "The provider credential or endpoint environment variable is not configured."
        else:
            status = "ADAPTER_NOT_IMPLEMENTED"
            reason = "No approved outbound transport adapter is registered for this provider."
        return {
            "requested_provider": self.provider,
            "status": status,
            "model": provider_config.get("model"),
            "external_call_allowed": False,
            "credential_configured": credential_configured,
            "reason": reason,
        }

    @staticmethod
    def _live_block_is_attributable(block: dict[str, Any]) -> bool:
        required = (
            "observed_at",
            "evidence_refs",
            "verification_target",
            "verification_check_id",
            "verification_outcome",
        )
        return (
            all(block.get(field) for field in required)
            and isinstance(block.get("evidence_refs"), list)
            and block.get("verification_outcome") == "success"
            and block.get("trust_level") == 5
        )

    @classmethod
    def _normalise_evidence_pack(cls, prompt: str, evidence_pack: Any) -> dict[str, Any]:
        """Drop malformed evidence before it reaches any response or provider request."""
        raw_pack = evidence_pack if isinstance(evidence_pack, dict) else {}
        unknowns = [
            item for item in raw_pack.get("unknowns", []) if isinstance(item, str) and item
        ]
        accepted_blocks: list[dict[str, Any]] = []
        for index, block in enumerate(raw_pack.get("evidence_blocks", [])):
            if not isinstance(block, dict):
                unknowns.append(f"Evidence block {index + 1} was malformed and excluded.")
                continue
            status = block.get("evidence_status")
            trust_level = block.get("trust_level")
            if (
                status not in {"documented", "live_verified"}
                or not isinstance(block.get("source_file"), str)
                or not block.get("source_file")
                or not isinstance(block.get("content"), str)
                or not isinstance(trust_level, int)
                or not 1 <= trust_level <= 5
            ):
                unknowns.append(f"Evidence block {index + 1} lacked required attribution and was excluded.")
                continue
            if status == "documented" and trust_level > 3:
                unknowns.append(
                    f"Evidence block {index + 1} assigned live-level trust to documentation and was excluded."
                )
                continue
            if status == "live_verified" and not cls._live_block_is_attributable(block):
                unknowns.append(f"Evidence block {index + 1} lacked complete live verification metadata and was excluded.")
                continue
            accepted_blocks.append(dict(block))

        if not accepted_blocks and not unknowns:
            unknowns.append("No accepted evidence was supplied.")
        return {
            "question": prompt,
            "sources": [block["source_file"] for block in accepted_blocks],
            "evidence_blocks": accepted_blocks,
            "unknowns": unknowns,
        }

    def build_provider_request(
        self, prompt: str, evidence_pack: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Build a bounded, secret-free request description without sending it."""
        normalised_pack = self._normalise_evidence_pack(prompt, evidence_pack)
        context = "\n\n".join(
            block.get("content", "") for block in normalised_pack["evidence_blocks"]
        )[:6000]
        provider = self.provider_status()
        return {
            "requested_provider": self.provider,
            "requested_model": provider["model"],
            "provider_status": provider["status"],
            "external_call_allowed": False,
            "system_instruction": (
                "Answer only from the supplied evidence. Distinguish documented context from "
                "current live evidence. State unknowns, and never claim health, verification, "
                "root cause, or remediation without attributable supporting evidence."
            ),
            "user_prompt": prompt,
            "evidence_context": context,
            "evidence_sources": normalised_pack["sources"],
            "max_output_tokens": int(self.config.get("max_output_tokens", 1024)),
        }

    def generate_response(
        self, prompt: str, evidence_pack: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Generate a deterministic response; never perform an outbound call."""
        normalised_pack = self._normalise_evidence_pack(prompt, evidence_pack)
        structured = StructuredAnswerBuilder().build(prompt, normalised_pack)
        requested_provider = self.provider_status()
        local_config = self.config.get("providers", {}).get(self.LOCAL_PROVIDER, {})
        return {
            "provider": self.LOCAL_PROVIDER,
            "requested_provider": self.provider,
            "requested_provider_status": requested_provider["status"],
            "model": local_config.get("model", "mne-brain-local-v2"),
            "status": "SUCCESS",
            "response_text": structured["response_text"],
            "trust_level": structured["trust_level"],
            "sources": structured["sources"],
            "evidence_status": structured["status"],
            "unknowns": structured["unknowns"],
            "external_call_attempted": False,
            "provider_reason": requested_provider["reason"],
        }


if __name__ == "__main__":
    result = LLMAdapter().generate_response("Check network status")
    print(result["response_text"])
