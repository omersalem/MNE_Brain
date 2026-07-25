---
name: "discover"
description: "Ingest new documentation, extract structured entity facts, execute embedded Live Verification for missing facts, and enrich the Digital Twin."
---

# Skill: Discover (`skills/discover/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`. Enforces Order of Trust (Live Infrastructure > Vault Notes).

## 1. Purpose
Ingest documentation and continuously enrich the Digital Twin. Automatically triggers Live Verification whenever imported knowledge is incomplete or missing technical telemetry.

## 2. Embedded Live Verification Workflow
1. **Import & Parse Documentation:** Parse raw Markdown files from `company_docs` or user uploads.
2. **Extract Structured Facts & Evaluate Confidence:** Extract IPs, VLANs, software versions, and hardware models. Assign confidence (`VERIFIED`, `HIGH`, `MEDIUM`, `LOW`).
3. **Trigger Embedded Live Verification:** If imported facts are incomplete or missing, check Connection Profiles (`00_meta/05_connections/`) and recommend read-only Live Verification using target connectors (`fortigate`, `cisco`, `f5`, `windows`, `vmware`, `linux`).
4. **Update Vault Knowledge:** Write enriched entity notes, update frontmatter (`last_review`, `confidence_score`), and elevate rating to `VERIFIED`.
5. **Preserve Human Notes:** Preserve all human prose (`## Notes`). Never overwrite manual documentation automatically.
6. **Generate Discovery Report:** Output a structured enrichment report in `50_operations_and_knowledge/54_ai_discovery/`.
