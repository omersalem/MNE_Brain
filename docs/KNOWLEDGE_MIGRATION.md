# Canonical Knowledge Migration

## Purpose

This migration makes every Release 2 knowledge note attributable and honest about its evidence state. It is non-destructive: no legacy note is deleted or relabeled as live evidence during the migration.

## Required metadata

Every canonical note must comply with `00_meta/schemas/canonical-note.schema.json` and include:

- a stable `id`, `name`, `category`, and aliases;
- a named owner and relationships to other entities;
- `knowledge_status`, source, verification timestamp, and freshness TTL;
- `evidence_refs`, verification target, check ID, and successful outcome when and only when the status is `live_verified`;
- optional declared `facts` only when the values are attributable and suitable for later drift comparison.

## Migration order

1. Network and security edge devices and their dependent services.
2. Identity, DNS, and Exchange dependencies.
3. Compute, virtualization, backup, and storage.
4. Applications, service owners, user impact, and branch topology.

For each note, preserve the existing body, add source metadata, choose `documented` or `unverified` unless accepted live evidence exists, and record conflicting identifiers for sole-owner review. Do not infer live status from old documents or generated outputs. A drift finding may create an owner-review proposal only when persistence is explicitly requested, and it must never overwrite the canonical note automatically.

The initial migration may use `source: legacy_release_2_import`, `knowledge_status: unverified`, `last_verified: null`, and `freshness_ttl_hours: 720`. These values describe migration state and a 30-day review interval; they are not evidence of current infrastructure state.

## Audit commands

```powershell
python scripts/audit_canonical_knowledge.py
python scripts/audit_canonical_knowledge.py --strict
```

The default command reports gaps without changing files. Strict mode is for CI only after all notes have been migrated.
