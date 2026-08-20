#!/usr/bin/env python3
"""Deterministic, metadata-preserving entity index for canonical knowledge."""

import argparse
import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


class EntityIndexBuilder:
    """Build an in-memory entity index without inferring operational truth."""

    _index_lock = threading.Lock()
    _index_cache: dict[str, dict[str, Any]] = {}
    _lookup_cache: dict[str, dict[str, dict[str, list[dict[str, Any]]]]] = {}

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.knowledge_dir = self.base_dir / "knowledge"
        self.output_file = self.base_dir / "00_meta" / "indices" / "entity-index.json"

    @staticmethod
    def _as_string_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return sorted({item for item in value if isinstance(item, str) and item})
        return []

    def build_index(self, *, persist: bool = False) -> dict[str, Any]:
        """Parse canonical-note frontmatter into a stable entity index.

        The default is in-memory only. Persisting an index is an explicit build
        action and must not happen as a side effect of answering a question.
        """
        entities: list[dict[str, Any]] = []
        seen_ids: dict[str, str] = {}

        for md_path in sorted(self.knowledge_dir.rglob("*.md")):
            content = md_path.read_text(encoding="utf-8")
            if not content.startswith("---"):
                continue

            parts = content.split("---", 2)
            if len(parts) < 3:
                continue
            metadata = yaml.safe_load(parts[1]) or {}
            if not isinstance(metadata, dict):
                continue

            entity_id = str(metadata.get("id", md_path.stem))
            id_key = entity_id.casefold()
            rel_path = md_path.relative_to(self.base_dir).as_posix()
            if id_key in seen_ids:
                raise ValueError(
                    f"Duplicate entity ID '{entity_id}' in {seen_ids[id_key]} and {rel_path}"
                )
            seen_ids[id_key] = rel_path

            ip = metadata.get("ip")
            ip_addresses = [ip] if isinstance(ip, str) and ip else []
            entities.append(
                {
                    "entity_id": entity_id,
                    "name": str(metadata.get("name", md_path.stem)),
                    "category": str(metadata.get("category", md_path.parent.name)),
                    "aliases": self._as_string_list(metadata.get("aliases")),
                    "hostname": str(metadata.get("hostname", "")),
                    "fqdn": str(metadata.get("fqdn", "")),
                    "ip": ip_addresses[0] if ip_addresses else "",
                    "ip_addresses": ip_addresses,
                    "vlan": metadata.get("vlan", ""),
                    "services": self._as_string_list(metadata.get("services")),
                    "owner": str(metadata.get("owner", "")),
                    "related_entities": self._as_string_list(metadata.get("related_entities")),
                    "knowledge_status": str(metadata.get("knowledge_status", "unverified")),
                    "source": metadata.get("source"),
                    "last_verified": metadata.get("last_verified"),
                    "freshness_ttl_hours": metadata.get("freshness_ttl_hours"),
                    "evidence_refs": self._as_string_list(metadata.get("evidence_refs")),
                    "verification_target": str(metadata.get("verification_target", "")),
                    "verification_check_id": str(metadata.get("verification_check_id", "")),
                    "verification_outcome": str(metadata.get("verification_outcome", "")),
                    "canonical_file": rel_path,
                }
            )

        index_data = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "total_entities": len(entities),
            "entities": sorted(entities, key=lambda entity: entity["entity_id"].casefold()),
        }
        exact_lookup: dict[str, list[dict[str, Any]]] = {}
        alias_lookup: dict[str, list[dict[str, Any]]] = {}
        service_lookup: dict[str, list[dict[str, Any]]] = {}
        for entity in index_data["entities"]:
            for term in (entity["entity_id"], entity["hostname"], entity["fqdn"], entity["ip"]):
                if term:
                    exact_lookup.setdefault(term.casefold(), []).append(entity)
            for term in (entity["name"], *entity["aliases"]):
                if term:
                    alias_lookup.setdefault(term.casefold(), []).append(entity)
            for term in entity.get("services", []):
                if term:
                    service_lookup.setdefault(term.casefold(), []).append(entity)
        with self._index_lock:
            cache_key = str(self.base_dir.resolve())
            self.__class__._index_cache[cache_key] = index_data
            self.__class__._lookup_cache[cache_key] = {
                "exact": exact_lookup,
                "alias": alias_lookup,
                "service": service_lookup,
            }
            if persist:
                self.output_file.parent.mkdir(parents=True, exist_ok=True)
                self.output_file.write_text(json.dumps(index_data, indent=2), encoding="utf-8")
        return index_data

    @staticmethod
    def _matches_term(question: str, term: str) -> bool:
        if not term:
            return False
        return bool(re.search(r"(?<![A-Za-z0-9_-])" + re.escape(term.casefold()) + r"(?![A-Za-z0-9_-])", question.casefold()))

    def resolve_entity(self, query: str) -> list[dict[str, Any]]:
        """Return deterministically ordered, matching entities without guessing."""
        cache_key = str(self.base_dir.resolve())
        if cache_key not in self.__class__._index_cache:
            self.build_index()

        query_key = query.casefold().strip()
        candidate_terms = {
            query_key,
            *(token.casefold() for token in re.findall(r"[A-Za-z0-9_.:-]+", query)),
        }
        lookup = self.__class__._lookup_cache.get(cache_key, {})

        def lookup_candidates(kind: str) -> list[dict[str, Any]]:
            matched: dict[str, dict[str, Any]] = {}
            term_map = lookup.get(kind, {})
            for term in candidate_terms:
                for entity in term_map.get(term, []):
                    matched[entity["entity_id"]] = entity
            return sorted(matched.values(), key=lambda entity: entity["entity_id"].casefold())

        exact_matches = lookup_candidates("exact")
        if exact_matches:
            return exact_matches
        alias_matches = lookup_candidates("alias")
        if alias_matches:
            return alias_matches
        service_matches = lookup_candidates("service")
        if service_matches:
            return service_matches

        matches: list[tuple[int, dict[str, Any]]] = []
        for entity in self.__class__._index_cache[cache_key].get("entities", []):
            exact_terms = [entity["entity_id"], entity["hostname"], entity["fqdn"], entity["ip"]]
            alias_terms = [entity["name"], *entity["aliases"]]
            if any(self._matches_term(query, term) for term in exact_terms):
                matches.append((0, entity))
            elif any(self._matches_term(query, term) for term in alias_terms):
                matches.append((1, entity))

        return [entity for _, entity in sorted(matches, key=lambda item: (item[0], item[1]["entity_id"].casefold()))]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the MNE Brain entity index")
    parser.add_argument("--write", action="store_true", help="Persist the generated index")
    args = parser.parse_args()
    result = EntityIndexBuilder().build_index(persist=args.write)
    print(f"Indexed {result['total_entities']} canonical entities.")
