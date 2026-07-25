---
name: "explain"
description: "Explain network topologies and path flows using Evidence-Driven reasoning."
---

# Skill: Explain (`skills/explain/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Explain multi-tier network topologies and dependencies while ranking path hypotheses using evidence strength.

## 2. Layered Workflow
1. **Map Traffic Path:** Explain how traffic flows end-to-end (`Client ➔ Core ➔ FortiGate ➔ FTD ➔ F5 ➔ Workload`).
2. **Rank Path Hypotheses:** Categorize path hops using qualitative evidence ranks (`Primary`, `Secondary`, `Possible`, `Unlikely`, `Eliminated`).
3. **Declare Confidence:** Attach Verification Summary with explicit evidence citations.
