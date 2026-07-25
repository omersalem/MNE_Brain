---
name: "explain"
description: "Explain topologies and traffic flows for Explain and Design intents. Escalates to Investigation Mode for live path issues."
---

# Skill: Explain (`skills/explain/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Explain multi-tier network topologies and traffic flows. Responds to **Explain** and **Design** intents using Quick Mode; escalates to Investigation Mode for live path troubleshooting.

## 2. Intent-Based Workflow
- **Explain / Design Intent (Quick Mode):** Provide fast, structured explanations of network design and component roles.
- **Escalation to Investigation Mode:** For live path troubleshooting or unconfirmed hops (`Client ➔ Switch ➔ Core ➔ FortiGate ➔ FTD ➔ F5 ➔ Workload`), escalate to Investigation Mode, recommend hop-by-hop read-only Live Verification, and attach a Verification Summary.
