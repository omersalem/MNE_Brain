---
name: "review"
description: "Audit vault quality, broken Wiki links, orphan documents, SPOF path risks, and recommend Live Verification to resolve gaps."
---

# Skill: Review (`skills/review/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Audit vault quality, freshness, broken Wiki links, orphan documents, and Single Point of Failure (SPOF) path risks. Automatically recommends Live Verification to resolve detected documentation gaps.

## 2. Embedded Live Verification Workflow
1. **Audit Vault Health & Schemas:** Inspect frontmatter schemas (`tpl-*.md`), link integrity (`[[Entity]]`), and compute Vault Health Score via `quality_evaluator.py`.
2. **Detect Documentation Gaps & Conflicts:** Identify outdated notes, conflicting policies, or unverified IP assignments.
3. **Trigger Embedded Live Verification:** Recommend read-only Live Verification using target connectors to resolve detected conflicts and elevate vault confidence ratings to `VERIFIED`.
4. **Generate Quality Audit Reports:** Commit actionable audit reports and SPOF path findings to `50_operations_and_knowledge/54_ai_discovery/`. Never modify documentation automatically during a review pass.
