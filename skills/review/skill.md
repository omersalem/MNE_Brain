---
name: "review"
description: "Audit vault quality, broken links, SPOFs, and confidence ratings for Review and Audit intents."
---

# Skill: Review (`skills/review/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Audit vault quality, freshness, broken Wiki links, orphan documents, and Single Point of Failure (SPOF) risks for **Review** and **Audit** intents.

## 2. Intent-Based Workflow
- **Review / Audit Intent (Quick Mode):** Check frontmatter schemas (`tpl-*.md`), link integrity (`[[Entity]]`), and compute Vault Health Score via `quality_evaluator.py`.
- **Escalation to Investigation Mode:** When outdated notes, conflicting policies, or unverified IPs are detected, escalate to Investigation Mode, recommend read-only Live Verification, and commit audit reports with Verification Summaries.
