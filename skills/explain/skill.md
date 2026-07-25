---
name: "explain"
description: "Explain network topologies, multi-device traffic flows, and component dependencies using Evidence-Based Reasoning."
---

# Skill: Explain (`skills/explain/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Explain multi-tier network topologies, traffic flows, and component dependencies while distinguishing documentation from live reality.

## 2. Evidence-Based Explanation Workflow
1. **Trace Multi-Device Hop Paths:** Map traffic flows sequentially: `Client ➔ Switch ➔ Core ➔ FortiGate ➔ FTD ➔ F5 ➔ Workload`.
2. **Classify Path Telemetry:** Categorize each hop into *Verified Facts* (confirmed via telemetry) or *Documented Facts* (vault docs).
3. **Declare Confidence & State Unknowns:** Never present assumptions as verified facts. Clearly state unknown hop parameters.
4. **Conclude with Verification Summary:** Attach standard Verification Summary block with hop-by-hop Live Verification recommendations.
