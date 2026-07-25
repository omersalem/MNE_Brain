---
name: "explain"
description: "Explain network topologies and path flows using Senior SRE / TAC reasoning standards."
---

# Skill: Explain (`skills/explain/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Explain multi-tier network topologies and dependencies using Cisco TAC / SRE reasoning standards.

## 2. Layered Workflow
1. **Map Traffic Path:** Explain how traffic flows end-to-end (`Client ➔ Core ➔ FortiGate ➔ FTD ➔ F5 ➔ Workload`).
2. **Select Authoritative Inspection Targets:** Identify Level 1/2 verification hops that maximize Information Gain.
3. **Declare Confidence & Stop Condition:** Attach Verification Summary with explicit evidence citations.
