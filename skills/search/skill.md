---
name: "search"
description: "Search across all vault notes, profiles, runbooks, and graph links. Classifies search results using Evidence-Based Reasoning."
---

# Skill: Search (`skills/search/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Search the entire Brain for infrastructure objects while strictly separating Verified Facts, Documented Facts, Assumptions, and Unknown information.

## 2. Evidence-Based Search Workflow
1. **Traverse Vault Indices & Canonical Notes:** Search domain indices (`00_meta/04_indices/`), entity notes, profiles, and runbooks.
2. **Classify Search Results:** Categorize findings into Documented Facts (vault notes) or Verified Facts (live telemetry).
3. **Handle Missing Objects:** If an object is unknown, do NOT assume non-existence; list it as *Unknown* and recommend read-only Live Verification.
4. **Conclude with Verification Summary:** Attach standard Verification Summary block detailing sources, confidence, and recommended next actions.
