---
name: "discover"
description: "Ingest documentation and execute Live Verification to enrich Layer 1 knowledge/ and Layer 2 operations/ discovery logs."
---

# Skill: Discover (`skills/discover/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Ingest documentation, run read-only live verification, and enrich permanent facts in `knowledge/` while recording discovery session logs in `operations/discovery/`.

## 2. Layered Workflow
1. **Search Layer 1 `knowledge/`:** Inspect existing entity notes and schemas.
2. **Execute Read-Only Live Verification:** If telemetry gaps exist, execute connectors and log raw session reports into `operations/discovery/`.
3. **Knowledge Promotion to `knowledge/`:** Promote verified long-term facts into `knowledge/` entity notes with `VERIFIED` confidence ratings.
4. **Preserve Human Notes:** Keep human prose 100% intact.
