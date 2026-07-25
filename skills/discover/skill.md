---
name: "discover"
description: "Ingest documentation and execute Evidence-Ranked verification for Live Discovery."
---

# Skill: Discover (`skills/discover/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Ingest documentation and enrich `knowledge/`. Uses the Evidence Ranking Engine to target missing telemetry gaps.

## 2. Layered Workflow
1. **Parse & Extract Facts:** Extract entity facts and map to `knowledge/` notes.
2. **Formulate Evidence Matrix:** Identify missing telemetry evidence and rank discovery hypotheses.
3. **Execute Read-Only Live Verification:** Log session reports into `operations/discovery/`.
4. **Promote Facts to `knowledge/`:** Update frontmatter metadata to `VERIFIED` while preserving human notes (`## Notes`).
