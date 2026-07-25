---
name: "review"
description: "Audit vault quality, SPOF path risks, and link integrity across Layer 1 knowledge/, Layer 2 operations/, and Layer 3 intelligence/."
---

# Skill: Review (`skills/review/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Audit Digital Twin health, link integrity, and SPOF risks across the 3-layer architecture.

## 2. Layered Workflow
1. **Audit Layer 1 `knowledge/`:** Verify frontmatter schemas (`tpl-*.md`) and Wiki links (`[[Entity]]`).
2. **Audit Layer 2 `operations/`:** Review incident frequency in `operations/incidents/` and verification logs in `operations/discovery/`.
3. **Promote Stable Incident Lessons:** Identify recurring incidents in `operations/incidents/` and promote reusable lessons into `intelligence/runbooks/`.
