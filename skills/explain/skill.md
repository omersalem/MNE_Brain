---
name: "explain"
description: "Explain network topologies, multi-device traffic flows, and component dependencies. Recommends Live Verification when path hops are unconfirmed."
---

# Skill: Explain (`skills/explain/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Explain multi-tier network topologies, traffic flows, and component dependencies. Automatically recommends Live Verification whenever path hop details are unconfirmed.

## 2. Embedded Live Verification Workflow
1. **Trace Multi-Device Hop Paths:** Map traffic flows sequentially: `Client ➔ Access Switch ➔ Core Switch ➔ FortiGate ➔ Cisco FTD ➔ F5 WAF ➔ Target Workload`.
2. **Evaluate Path Confidence:** Assign confidence rating (`VERIFIED`, `HIGH`, `MEDIUM`, `LOW`) to every hop in the path.
3. **Trigger Embedded Live Verification:** If any hop or policy in the path is unknown or unverified, state what is unknown and recommend read-only Live Verification across target devices instead of guessing.
4. **Explain Upstream & Downstream Dependencies:** Link related entities using bidirectional Wiki links (`[[Entity-Basename]]`). Never present assumptions as verified facts.
