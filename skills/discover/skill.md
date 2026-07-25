---
name: "discover"
description: "Ingest telemetry, execute read-only live verification, resolve knowledge gaps, update Wiki links, and enrich the Digital Twin."
---

# Skill: Discover (`skills/discover/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`. Enforces Evidence-Based Reasoning.

## 1. Purpose
Ingest documentation and continuously enrich the Digital Twin. Classifies findings into *Verified Facts*, *Documented Facts*, *Assumptions*, and *Unknown*, appending a Verification Summary to all outputs.

## 2. Evidence-Based Discovery Workflow
1. **Import & Parse Documentation:** Parse raw Markdown files from `company_docs` or user uploads.
2. **Classify Facts & Confidence:** Classify findings into Verified Facts, Documented Facts, Assumptions, and Unknown. Assign confidence (`VERIFIED`, `HIGH`, `MEDIUM`, `LOW`).
3. **Trigger Live Verification:** If confidence is `MEDIUM` or `LOW`, recommend read-only Live Verification using target connectors.
4. **Enrich Vault & Log History:** Write updated entity notes, elevate confidence rating to `VERIFIED`, and log transition in `80_ai_knowledge/version_history.jsonl`.
5. **Conclude with Verification Summary:** Attach standard Verification Summary block.
