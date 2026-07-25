---
name: "discover"
description: "Ingest documentation and execute Observation-Interpretation verification for Live Discovery."
---

# Skill: Discover (`skills/discover/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Ingest documentation and enrich `knowledge/`. Applies the Observation-Interpretation Framework to separate ingested facts from engineering hypotheses.

## 2. Layered Workflow
1. **Parse Observations:** Extract directly observed entity facts and map to `knowledge/` notes.
2. **Formulate Interpretations & Verification Plan:** Identify missing telemetry evidence and present non-destructive verification targets.
3. **Execute Read-Only Live Verification:** Log session reports into `operations/discovery/`.
4. **Promote Verified Conclusions:** Update frontmatter metadata to `VERIFIED` while preserving human notes (`## Notes`).
