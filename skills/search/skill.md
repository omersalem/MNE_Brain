---
name: "search"
description: "Search Layer 1 knowledge/ and Layer 3 intelligence/. Uses Level 1 passive read when queried objects are unverified."
---

# Skill: Search (`skills/search/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Search the Brain for infrastructure objects. If an object is unverified or missing, queries authoritative sources using Level 1 passive read actions.

## 2. Layered Workflow
1. **Search Layer 1 `knowledge/` & Layer 3 `intelligence/`:** Locate matching notes and Wiki links (`[[Entity-Basename]]`).
2. **Select Authoritative Source:** Query target gateway, DC, or vCenter for missing objects.
3. **Execute Read-Only Verification:** Conclude with standard Verification Summary block. Mask all credentials.
