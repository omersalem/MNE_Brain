---
name: "search"
description: "Search across Layer 1 knowledge/, Layer 3 intelligence/, and Layer 2 operations/ using intent-based retrieval."
---

# Skill: Search (`skills/search/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Provide deep intent-based search across the 3-layer architecture without scanning unnecessary folders.

## 2. Layered Search Strategy
- **Explain / Learn Intent:** Search `knowledge/` ➔ `intelligence/`.
- **Search / Lookup Intent:** Search `knowledge/` ➔ `intelligence/` ➔ `operations/` *(only if needed)*.
- **Review / Audit Intent:** Search `knowledge/` ➔ `operations/` ➔ `intelligence/`.
- If queried object is unverified, recommend read-only Live Verification (`operations/live-verification/`).
