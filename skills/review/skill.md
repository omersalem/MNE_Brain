---
name: "review"
description: "Audit vault quality, broken Wiki links, orphan documents, SPOF path risks, and attach Evidence-Based Verification Summaries."
---

# Skill: Review (`skills/review/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Audit vault quality, freshness, broken Wiki links, orphan documents, and Single Point of Failure (SPOF) path risks using Evidence-Based Reasoning.

## 2. Evidence-Based Review Workflow
1. **Audit Vault Health & Schemas:** Inspect frontmatter schemas (`tpl-*.md`), link integrity (`[[Entity]]`), and compute Vault Health Score via `quality_evaluator.py`.
2. **Classify Audit Findings:** Categorize findings into Verified Facts, Documented Facts, Assumptions, and Unknown Gaps.
3. **Recommend Verification & Remediation:** Recommend read-only Live Verification using target connectors to resolve detected documentation drift.
4. **Conclude with Verification Summary:** Attach standard Verification Summary block to all audit reports.
