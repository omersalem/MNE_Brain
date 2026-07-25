---
name: "search"
description: "Search across all vault notes and profiles. Uses Quick Mode for documented facts; escalates to Investigation Mode when objects are missing."
---

# Skill: Search (`skills/search/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Search the Brain for infrastructure objects. Operates in **Quick Mode** for standard vault lookups; escalates to **Investigation Mode** when queried objects are unverified or missing.

## 2. Operational Mode Workflow
- **Quick Mode (Documented Objects):** Search domain notes, profiles, and runbooks. Return concise findings with Wiki citations and confidence ratings.
- **Investigation Mode Escalation (Missing Objects):** If object (IP, MAC, VM, VLAN) is missing, do NOT assume non-existence. Recommend read-only Live Verification and attach a Verification Summary.
