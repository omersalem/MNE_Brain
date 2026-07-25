---
name: "explain"
description: "Explain network topologies, multi-device traffic flows, component dependencies, and declare explicit confidence ratings."
---

# Skill: Explain (`skills/explain/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Explain infrastructure topologies, multi-hop traffic paths, and incident root causes while strictly adhering to the Order of Trust and declaring explicit Confidence Ratings.

## 2. Core Responsibilities & Workflow
1. **Trace Multi-Device Hop Paths:** Map traffic sequentially: `Client ➔ Switch ➔ Core ➔ FortiGate ➔ FTD ➔ F5 WAF ➔ Workload`.
2. **Declare Confidence Rating:** Explicitly state answer confidence: `VERIFIED`, `HIGH`, `MEDIUM`, or `LOW`.
3. **Trigger Live Verification:** If confidence is `LOW` or `MEDIUM`, explain what is known/unknown and recommend read-only Live Verification instead of guessing.
4. **Highlight Dependencies:** Show upstream providers and downstream consumers using Wiki links (`[[Entity-Basename]]`).
