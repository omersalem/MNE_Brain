---
name: "discover"
description: "Ingest documentation and execute Investigation Mode live verification for Discover and Document intents."
---

# Skill: Discover (`skills/discover/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Ingest documentation and enrich the Digital Twin. Classifies incoming requests into **Discover** or **Document** intents.

## 2. Intent-Based Workflow
- **Discover / Document Intent (Quick Mode Pass):** Ingest raw Markdown files, parse entity facts, update frontmatter metadata and Wiki links (`[[Entity-Basename]]`).
- **Escalation to Investigation Mode:** If imported documentation contains unverified IP, route, or policy gaps, escalate to Investigation Mode, recommend read-only Live Verification using target connectors, and attach a Verification Summary.
