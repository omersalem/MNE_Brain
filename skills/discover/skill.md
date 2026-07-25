---
name: "discover"
description: "Ingest documentation and execute autonomous Level 1/2 read-only verification for Live Discovery."
---

# Skill: Discover (`skills/discover/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Ingest documentation and enrich `knowledge/`. Executes Level 1/2 read-only telemetry discovery autonomously while strictly prohibiting Level 3 configuration changes.

## 2. Layered Workflow
1. **Parse & Extract Facts:** Extract entity facts and map to `knowledge/` notes.
2. **Formulate Verification Action:** Classify inspection actions into Level 1 (Passive Read) or Level 2 (Active Verification).
3. **Execute Read-Only Live Verification:** Execute connectors autonomously according to level policy and log session reports into `operations/discovery/`.
4. **Promote Facts to `knowledge/`:** Update frontmatter metadata to `VERIFIED` while preserving human notes (`## Notes`).
