---
name: "review"
description: "Audit vault quality, broken links, SPOFs, and confidence ratings using Dual Operating Modes."
---

# Skill: Review (`skills/review/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Audit vault quality, freshness, broken Wiki links, orphan documents, and Single Point of Failure (SPOF) path risks using Dual Operating Modes.

## 2. Operational Mode Workflow
- **Quick Mode Audit:** Check frontmatter schemas (`tpl-*.md`), link integrity (`[[Entity]]`), and compute Vault Health Score via `quality_evaluator.py`.
- **Investigation Mode Audit:** When outdated notes, conflicting policies, or unverified IPs are detected, recommend read-only Live Verification to elevate vault confidence to `VERIFIED` and commit audit reports with Verification Summaries.
