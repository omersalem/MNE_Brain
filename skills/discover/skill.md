---
name: "discover"
description: "Ingest documentation and execute Investigation Mode live verification to enrich Digital Twin canonical notes."
---

# Skill: Discover (`skills/discover/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Ingest documentation and enrich the Digital Twin. Automatically operates in **Investigation Mode** when incoming documentation contains unverified IP, route, or policy gaps.

## 2. Operational Mode Workflow
- **Quick Mode Pass:** Ingest raw Markdown files, parse entity facts, update YAML frontmatter and Wiki links (`[[Entity-Basename]]`).
- **Investigation Mode Escalation:** If telemetry is missing, recommend read-only Live Verification using target connectors, enrich vault notes, and attach a Verification Summary.
