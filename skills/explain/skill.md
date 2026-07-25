---
name: "explain"
description: "Explain network topologies and path flows using Layer 1 knowledge/ and Layer 3 intelligence/ runbooks."
---

# Skill: Explain (`skills/explain/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Explain multi-tier network topologies and dependencies using permanent facts from `knowledge/` and SOP runbooks from `intelligence/runbooks/`.

## 2. Layered Workflow
1. **Query Layer 1 `knowledge/`:** Map entity topology facts and bidirectional Wiki links (`[[Entity-Basename]]`).
2. **Query Layer 3 `intelligence/`:** Pull relevant SOP runbooks or troubleshooting patterns.
3. **Declare Confidence & Verification Summary:** Attach standard Verification Summary.
