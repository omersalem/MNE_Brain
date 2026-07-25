---
name: "explain"
description: "Explain network topologies and path flows. Uses Quick Mode for design docs; escalates to Investigation Mode for live traffic paths."
---

# Skill: Explain (`skills/explain/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Explain multi-tier network topologies, traffic flows, and component dependencies. Uses **Quick Mode** for static architectural explanations; escalates to **Investigation Mode** for live path troubleshooting.

## 2. Operational Mode Workflow
- **Quick Mode (Architecture & Design):** Provide fast, structured explanations of network design and component roles.
- **Investigation Mode (Live Path Troubleshooting):** Map multi-hop paths (`Client ➔ Switch ➔ Core ➔ FortiGate ➔ FTD ➔ F5 ➔ Workload`), declare confidence (`VERIFIED`, `HIGH`, `MEDIUM`, `LOW`), recommend hop-by-hop read-only Live Verification, and attach a Verification Summary.
