#!/usr/bin/env python3
"""Build focused evidence packs without inventing or upgrading evidence."""

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class EvidencePackBuilder:
    """Select only attributable, currently usable canonical evidence."""

    ACCEPTED_STATUSES = {"documented", "live_verified"}

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.max_token_budget = 1500

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Use a stable conservative token estimate for context budgeting."""
        return max(1, len(text) // 4)

    @staticmethod
    def _as_source_text(value: Any) -> str:
        if isinstance(value, list):
            return "; ".join(str(item) for item in value)
        return str(value or "unknown source")

    @staticmethod
    def _as_observed_at(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _live_evidence_is_fresh(entity: dict[str, Any]) -> bool:
        """A malformed or expired live-verification record is never accepted."""
        if entity.get("knowledge_status") != "live_verified":
            return True
        if not entity.get("evidence_refs"):
            return False
        try:
            observed_at = str(entity["last_verified"]).replace("Z", "+00:00")
            observed = datetime.fromisoformat(observed_at)
            if observed.tzinfo is None:
                return False
            ttl_hours = int(entity["freshness_ttl_hours"])
        except (KeyError, TypeError, ValueError):
            return False
        age_seconds = (datetime.now(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds()
        return 0 <= age_seconds <= ttl_hours * 3600

    def _entity_block(self, entity: dict[str, Any]) -> dict[str, Any]:
        canonical_path = self.base_dir / entity["canonical_file"]
        body = ""
        if canonical_path.exists():
            raw_text = canonical_path.read_text(encoding="utf-8")
            parts = raw_text.split("---", 2)
            body = parts[2].strip() if len(parts) >= 3 else raw_text.strip()

        content = "\n".join(
            [
                f"Entity: {entity['name']}",
                f"Category: {entity['category']}",
                f"Status: {entity['knowledge_status']}",
                f"Source: {self._as_source_text(entity.get('source'))}",
                f"Identifiers: {', '.join([*entity.get('ip_addresses', []), *entity.get('aliases', [])])}",
                body[:900],
            ]
        ).strip()
        status = entity["knowledge_status"]
        return {
            "entity_id": entity["entity_id"],
            "source_file": entity["canonical_file"],
            "source": self._as_source_text(entity.get("source")),
            "trust_level": 5 if status == "live_verified" else 3,
            "evidence_status": status,
            "observed_at": self._as_observed_at(entity.get("last_verified")),
            "evidence_refs": entity.get("evidence_refs", []),
            "verification_target": entity.get("verification_target", ""),
            "verification_check_id": entity.get("verification_check_id", ""),
            "verification_outcome": entity.get("verification_outcome", ""),
            "heading": f"Canonical evidence — {entity['name']}",
            "content": content,
        }

    def build_evidence_pack(
        self,
        question: str,
        target_entities: list[dict[str, Any]] | None = None,
        *,
        supplemental_evidence: list[dict[str, Any]] | None = None,
        persist: bool = False,
    ) -> dict[str, Any]:
        """Build an attributable pack; unverified records become explicit unknowns."""
        evidence_id = f"ev-{uuid.uuid4().hex[:8]}"
        sources: list[str] = []
        evidence_blocks: list[dict[str, Any]] = []
        unknowns: list[str] = []
        total_tokens = 0
        target_entity_ids = {
            str(entity.get("entity_id")) for entity in target_entities or [] if entity.get("entity_id")
        }
        accepted_evidence_ids: set[str] = set()

        for record in supplemental_evidence or []:
            if not isinstance(record, dict):
                unknowns.append("A supplemental evidence record was malformed and excluded.")
                continue
            if record.get("evidence_status") == "simulated":
                unknowns.append("Simulated transport output cannot support an operational conclusion.")
                continue
            required = (
                "evidence_id",
                "entity_id",
                "source_file",
                "source",
                "observed_at",
                "expires_at",
                "evidence_refs",
                "verification_target",
                "verification_check_id",
                "verification_outcome",
                "content",
            )
            if (
                record.get("evidence_status") != "live_verified"
                or record.get("trust_level") != 5
                or any(not record.get(field) for field in required)
                or record.get("verification_outcome") != "success"
                or record.get("entity_id") not in target_entity_ids
                or record.get("verification_target") != record.get("entity_id")
                or not isinstance(record.get("evidence_refs"), list)
                or record.get("evidence_id") not in record.get("evidence_refs", [])
            ):
                unknowns.append("A supplemental live-evidence record lacked required attribution and was excluded.")
                continue
            try:
                observed_at = datetime.fromisoformat(str(record["observed_at"]).replace("Z", "+00:00"))
                expires_at = datetime.fromisoformat(str(record["expires_at"]).replace("Z", "+00:00"))
            except ValueError:
                unknowns.append("A supplemental live-evidence timestamp was invalid and excluded.")
                continue
            now = datetime.now(timezone.utc)
            if (
                observed_at.tzinfo is None
                or expires_at.tzinfo is None
                or observed_at.astimezone(timezone.utc) > now
                or expires_at.astimezone(timezone.utc) <= now
                or expires_at <= observed_at
            ):
                unknowns.append("A supplemental live-evidence record was expired or temporally invalid.")
                continue
            evidence_id = str(record["evidence_id"])
            if evidence_id in accepted_evidence_ids:
                unknowns.append(f"Duplicate supplemental evidence {evidence_id} was excluded.")
                continue
            content = str(record["content"])
            block_tokens = self.estimate_tokens(content)
            if total_tokens + block_tokens > self.max_token_budget:
                unknowns.append(
                    f"Supplemental evidence {evidence_id} was excluded to preserve the token budget."
                )
                continue
            accepted_evidence_ids.add(evidence_id)
            evidence_blocks.append(dict(record))
            sources.append(str(record["source_file"]))
            total_tokens += block_tokens

        for entity in target_entities or []:
            status = entity.get("knowledge_status", "unverified")
            if status not in self.ACCEPTED_STATUSES:
                unknowns.append(
                    f"{entity['entity_id']} is {status}; it cannot support an operational conclusion."
                )
                continue
            if not self._live_evidence_is_fresh(entity):
                unknowns.append(
                    f"{entity['entity_id']} has expired or incomplete live-verification metadata."
                )
                continue

            block = self._entity_block(entity)
            block_tokens = self.estimate_tokens(block["content"])
            if total_tokens + block_tokens > self.max_token_budget:
                unknowns.append(
                    f"Evidence for {entity['entity_id']} was excluded to preserve the token budget."
                )
                continue
            evidence_blocks.append(block)
            sources.append(entity["canonical_file"])
            total_tokens += block_tokens

        if not target_entities:
            unknowns.append("No resolved entity was supplied; no generic infrastructure facts were assumed.")
        elif not evidence_blocks and not unknowns:
            unknowns.append("No accepted evidence was available for the resolved entities.")

        pack = {
            "evidence_id": evidence_id,
            "question": question,
            "total_tokens": total_tokens,
            "max_token_budget": self.max_token_budget,
            "sources": sources,
            "evidence_blocks": evidence_blocks,
            "unknowns": unknowns,
        }

        if persist:
            output_path = self.base_dir / "00_meta" / "indices" / "evidence-pack.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
        return pack


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build a focused MNE Brain evidence pack")
    parser.add_argument("--question", required=True)
    parser.add_argument("--write", action="store_true", help="Persist the generated pack")
    args = parser.parse_args()
    result = EvidencePackBuilder().build_evidence_pack(args.question, persist=args.write)
    print(json.dumps(result, indent=2))
