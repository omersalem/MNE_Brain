---
name: "explain"
description: "Explain network topologies and path flows using Information Gain reasoning."
---

# Skill: Explain (`skills/explain/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Explain multi-tier network topologies and dependencies while selecting verification actions based on Information Gain rather than topology sequence.

## 2. Layered Workflow
1. **Map Traffic Path:** Explain how traffic flows end-to-end (`Client ➔ Core ➔ FortiGate ➔ FTD ➔ F5 ➔ Workload`).
2. **Select Highest Information-Gain Hop:** When troubleshooting, select the hop that provides the highest Information Gain to eliminate unconfirmed path segments first.
3. **Declare Confidence & Stop Condition:** Attach Verification Summary with explicit Stop Conditions.
