---
name: "discover"
description: "Ingest documentation and execute Information-Gain verification for Live Discovery."
---

# Skill: Discover (`skills/discover/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Ingest documentation and enrich `knowledge/`. When telemetry gaps exist, calculates Information Gain vs. Cost to select the highest-value discovery action.

## 2. Layered Workflow
1. **Parse & Extract Facts:** Extract entity facts and map to `knowledge/` notes.
2. **Formulate Information Gain Plan:** If telemetry is unverified, define uncertainty, Information Gain rating, Operational Cost, and Stop Conditions.
3. **Execute Read-Only Live Verification:** Log session reports into `operations/discovery/`.
4. **Promote Facts to `knowledge/`:** Update frontmatter metadata to `VERIFIED` while preserving human notes (`## Notes`).
