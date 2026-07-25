---
name: "search"
description: "Search across all canonical entity notes, connection profiles, runbooks, incidents, indices, and Wiki graph links in the vault."
---

# Skill: Search (`skills/search/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Provide precise, deep, multi-domain search across all Markdown documentation, Connection Profiles (`00_meta/05_connections/`), Runbooks (`51_runbooks/`), Incident records (`53_incidents/`), and graph relationships.

## 2. Core Responsibilities & Workflow
1. **Multi-Domain Index Traversal:** Search domain index files (`00_meta/04_indices/`) and target entity notes sequentially.
2. **Extract & Merge Matching Facts:** Gather matching IP assignments, VLAN tags, firewall policy IDs, and server workloads.
3. **Rank Relevance & Confidence:** Evaluate evidence sources and assign confidence scores ($0.0 - 1.0$).
4. **Highlight Sources & Citations:** Explicitly reference canonical notes via Wiki links (e.g., `[[fw-fortigate-hq-01]]`).
5. **Identify Data Conflicts:** Flag any discrepancies between manual notes and live discovery profiles.

## 3. Strict Prohibitions
- Never invent search results or present unverified assumptions as facts.
- Never display raw passwords or private keys in search outputs.
