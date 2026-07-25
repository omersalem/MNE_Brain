---
name: "explain"
description: "Explain network topologies and path flows using Observation-Interpretation reasoning standards."
---

# Skill: Explain (`skills/explain/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Explain multi-tier network topologies and dependencies while strictly separating observed path facts from interpretations.

## 2. Layered Workflow
1. **Map Observed Path Facts:** Detail verified topology paths (`Client ➔ Core ➔ FortiGate ➔ FTD ➔ F5 ➔ Workload`).
2. **Formulate Interpretations for Unconfirmed Hops:** Use qualified engineering language for unverified hops.
3. **Declare Confidence & Conclusions:** Produce verified conclusions ONLY for hops backed by live telemetry.
