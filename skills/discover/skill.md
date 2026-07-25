---
name: "discover"
description: "Ingest new infrastructure documentation, enrich canonical entity notes, extract structured facts, update Wiki links, and maintain the Digital Twin."
---

# Skill: Discover (`skills/discover/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`. Enforces 100% read-only safety and human note preservation.

## 1. Purpose
Continuously enrich and maintain the Ministry Infrastructure Digital Twin by importing raw documentation, extracting structured entity facts, and updating Wiki relationships.

## 2. Core Responsibilities & Workflow
1. **Read & Import Documentation:** Parse raw Markdown files from `company_docs` or user uploads.
2. **Extract Structured Facts:** Identify verified IP addresses, VLAN IDs, MAC addresses, software versions, and hardware models.
3. **Detect Conflicts & Duplicates:** Compare newly extracted facts against existing canonical notes in domain subfolders (`10_network_and_security`, `20_compute_and_virtualization`, etc.).
4. **Update Metadata & Wiki Links:** Update YAML frontmatter fields (`last_review`, `confidence_score`) and establish bidirectional Wiki links (`[[Entity-Basename]]`).
5. **Preserve Human Notes:** Preserve all human-authored prose sections (`## Notes`, `## Custom Configurations`). Never overwrite user notes automatically.
6. **Generate Enrichment Report:** Output a structured summary report in `50_operations_and_knowledge/54_ai_discovery/`.

## 3. Strict Prohibitions
- Never invent missing infrastructure facts; label missing telemetry as `UNVERIFIED`.
- Never execute state-changing CLI/API configuration commands on live devices.
