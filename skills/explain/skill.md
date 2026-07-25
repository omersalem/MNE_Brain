---
name: "explain"
description: "Explain network topologies and path flows. Differentiates Traffic Path from Investigation Plan."
---

# Skill: Explain (`skills/explain/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Explain multi-tier network topologies and dependencies while clearly distinguishing Traffic Paths from Investigation Plans.

## 2. Layered Workflow
1. **Map Traffic Path:** Explain how traffic flows end-to-end (`Client ➔ Core ➔ FortiGate ➔ FTD ➔ F5 ➔ Workload`).
2. **Formulate Minimum Investigation Plan:** When troubleshooting, explain why only minimum target hops are inspected while other healthy path devices are excluded.
3. **Declare Confidence:** Attach Verification Summary with explicit exit criteria.
