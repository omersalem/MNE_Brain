---
name: "review"
description: "Audit vault quality, health metrics, broken Wiki links, orphan documents, single points of failure (SPOFs), and schema compliance."
---

# Skill: Review (`skills/review/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Audit the quality, completeness, consistency, freshness, and relationship integrity of the Ministry Infrastructure Digital Twin.

## 2. Core Responsibilities & Workflow
1. **Audit Vault Schema Compliance:** Verify that YAML frontmatter in entity notes matches `00_meta/02_schemas/tpl-*.md` templates.
2. **Detect Broken Wiki Links & Orphans:** Identify double-bracket links `[[Entity]]` that do not resolve to existing files, and notes missing parent links.
3. **Compute Vault Health Score:** Execute `quality_evaluator.py` to calculate completeness, freshness, and overall health metrics.
4. **Identify Infrastructure SPOFs:** Highlight single points of failure (single links, single VIPs, single hosts) in audit reports.
5. **Generate Quality Improvement Recommendations:** Produce actionable quality recommendations in `50_operations_and_knowledge/54_ai_discovery/`.

## 3. Strict Prohibitions
- Never modify or delete documentation automatically during a review pass.
- Never remove human-authored notes.
