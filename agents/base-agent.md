# Base AI Agent Operational Parent (`base-agent.md`)

> **Inheritance Notice:** This document is the secondary parent specification for all AI Agents. It inherits 100% of its governance, workflows, Evidence-Based Reasoning, and safety policies from `[[AGENTS.md]]`.

## 1. Purpose & Inheritance
- Common operational parent for all child agent profiles (`antigravity.md`, `codex.md`, `claude.md`, `opencode.md`, `pi.md`).
- Enforces the **Evidence-Based Infrastructure Reasoning** model and mandatory **Verification Summary** block across all AI models.

## 2. Operational Initialization & Response Pipeline
Upon booting, The AI Agent must:
1. Load `[[AGENTS.md]]` at repository root.
2. Load `[[base-agent.md]]`.
3. Search vault notes and classify findings into *Verified Facts*, *Documented Facts*, *Assumptions*, and *Unknown*.
4. Conclude every infrastructure response with the standardized **Verification Summary** block.
