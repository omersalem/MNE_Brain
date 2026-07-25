---
name: "discover"
description: "Ingest telemetry, execute read-only live verification, resolve knowledge gaps, update Wiki links, and enrich the Digital Twin."
---

# Skill: Discover (`skills/discover/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`. Enforces Order of Trust (Live Infrastructure > Vault Notes) and 100% read-only safety.

## 1. Purpose
Execute read-only live discovery and knowledge enrichment to convert `MEDIUM` or `LOW` confidence vault states into `VERIFIED` Digital Twin knowledge.

## 2. Core Responsibilities & Workflow
1. **Trigger Evaluation:** Automatically trigger when IP, firewall policy, route, or VM state is unverified.
2. **Execute Read-Only Discovery:** Use target connection profile in `00_meta/05_connections/` to run non-destructive inspection queries.
3. **Multi-Domain Inspection:** Route queries to target platforms (FortiGate, Cisco, F5, AD, Exchange, vCenter, Linux).
4. **Update Vault Knowledge:** Enrich YAML frontmatter, establish Wiki links (`[[Entity-Basename]]`), update confidence rating to `VERIFIED`.
5. **Preserve Human Notes:** Preserve all human prose (`## Notes`). Never overwrite manual notes.
6. **Output Discovery Report:** Generate report in `50_operations_and_knowledge/54_ai_discovery/`.
