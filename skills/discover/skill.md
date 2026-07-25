---
name: "discover"
description: "Ingest documentation and execute minimum-device Investigation Planning for Live Discovery."
---

# Skill: Discover (`skills/discover/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Ingest documentation and enrich `knowledge/`. When telemetry gaps exist, formulates a minimum-device Investigation Plan before running discovery connectors.

## 2. Layered Workflow
1. **Parse & Extract Facts:** Extract entity facts and map to `knowledge/` notes.
2. **Formulate Investigation Plan:** If telemetry is unverified, define scope, blast radius, minimum devices required, and exit criteria.
3. **Execute Read-Only Live Verification:** Log session reports into `operations/discovery/`.
4. **Promote Facts to `knowledge/`:** Update frontmatter metadata to `VERIFIED` while preserving human notes (`## Notes`).
