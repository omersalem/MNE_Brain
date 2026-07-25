---
name: "review"
description: "Audit vault quality, broken links, SPOFs, and present Information Gain plans for drift remediation."
---

# Skill: Review (`skills/review/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Audit vault quality, link integrity, and SPOF path risks across `knowledge/`, `operations/`, and `intelligence/`.

## 2. Layered Workflow
1. **Audit Layer 1 `knowledge/`:** Check frontmatter schemas (`tpl-*.md`), link integrity (`[[Entity]]`), and compute Vault Health Score.
2. **Formulate Information Gain Plan:** When conflicting policies or unverified IPs are detected, present highest-value verification actions to resolve drift with minimal operational cost.
3. **Promote Stable Incident Lessons:** Promote recurring incident RCA lessons from `operations/incidents/` into `intelligence/runbooks/`.
