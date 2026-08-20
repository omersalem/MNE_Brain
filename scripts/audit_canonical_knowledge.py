#!/usr/bin/env python3
"""Read-only metadata audit for canonical knowledge notes."""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator


REQUIRED_FIELDS = (
    "id",
    "name",
    "category",
    "aliases",
    "owner",
    "related_entities",
    "knowledge_status",
    "source",
    "last_verified",
    "freshness_ttl_hours",
)
VALID_STATUSES = {
    "documented",
    "live_verified",
    "stale",
    "unverified",
    "failed",
    "not_run",
}


def parse_frontmatter(path: Path) -> tuple[dict[str, Any], str | None]:
    """Return YAML frontmatter without interpreting the note body."""
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {}, "not valid UTF-8"

    if not content.startswith("---"):
        return {}, "frontmatter missing"

    sections = content.split("---", 2)
    if len(sections) < 3:
        return {}, "frontmatter terminator missing"

    try:
        metadata = yaml.safe_load(sections[1]) or {}
    except yaml.YAMLError as exc:
        return {}, f"invalid YAML: {exc}"

    if not isinstance(metadata, dict):
        return {}, "frontmatter is not a mapping"
    return metadata, None


def audit_knowledge(knowledge_dir: Path, schema_path: Path) -> dict[str, Any]:
    """Audit metadata completeness and identity conflicts without writing files."""
    notes = sorted(knowledge_dir.rglob("*.md")) if knowledge_dir.exists() else []
    missing_by_field: Counter[str] = Counter()
    invalid_notes: list[dict[str, str]] = []
    status_counts: Counter[str] = Counter()
    ids: defaultdict[str, list[str]] = defaultdict(list)
    aliases: defaultdict[str, list[str]] = defaultdict(list)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)

    for note in notes:
        rel_path = note.relative_to(knowledge_dir.parent).as_posix()
        metadata, error = parse_frontmatter(note)
        if error:
            invalid_notes.append({"path": rel_path, "error": error})
            continue

        for validation_error in validator.iter_errors(metadata):
            field = ".".join(str(part) for part in validation_error.path) or "frontmatter"
            invalid_notes.append({"path": rel_path, "error": f"{field}: {validation_error.message}"})

        status = metadata.get("knowledge_status")
        for field in REQUIRED_FIELDS:
            value = metadata.get(field)
            if (
                field == "last_verified"
                and value is None
                and status in {"unverified", "failed", "not_run"}
            ):
                continue
            if value is None or value == "" or value == []:
                missing_by_field[field] += 1

        entity_id = metadata.get("id")
        if isinstance(entity_id, str) and entity_id:
            ids[entity_id.casefold()].append(rel_path)

        if status:
            if status not in VALID_STATUSES:
                invalid_notes.append({"path": rel_path, "error": f"invalid knowledge_status: {status}"})
            else:
                status_counts[status] += 1

            if status == "live_verified" and not metadata.get("evidence_refs"):
                invalid_notes.append({"path": rel_path, "error": "live_verified without evidence_refs"})

        raw_aliases = metadata.get("aliases", [])
        if isinstance(raw_aliases, list):
            for alias in raw_aliases:
                if isinstance(alias, str) and alias:
                    aliases[alias.casefold()].append(rel_path)
        elif raw_aliases:
            invalid_notes.append({"path": rel_path, "error": "aliases must be an array"})

    duplicate_ids = {
        entity_id: paths for entity_id, paths in ids.items() if len(paths) > 1
    }
    shared_aliases = {
        alias: paths for alias, paths in aliases.items() if len(paths) > 1
    }

    compliant = (
        not invalid_notes
        and not duplicate_ids
        and not missing_by_field
        and len(notes) > 0
    )
    return {
        "knowledge_root": str(knowledge_dir),
        "notes_scanned": len(notes),
        "compliant": compliant,
        "missing_metadata_by_field": dict(sorted(missing_by_field.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "invalid_notes": invalid_notes,
        "duplicate_entity_ids": duplicate_ids,
        "shared_aliases": shared_aliases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only canonical knowledge metadata audit")
    parser.add_argument(
        "--knowledge-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "knowledge",
        help="Knowledge directory to inspect",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "00_meta" / "schemas" / "canonical-note.schema.json",
        help="Canonical-note JSON schema to validate",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when the metadata contract is not yet met",
    )
    args = parser.parse_args()

    result = audit_knowledge(args.knowledge_dir, args.schema)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["compliant"] or not args.strict else 1


if __name__ == "__main__":
    sys.exit(main())
