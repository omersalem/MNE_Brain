# Base AI Agent Operational Parent (`base-agent.md`)

> **Inheritance Notice:** This document is the secondary parent specification for all AI Agents. It inherits 100% of its governance, workflows, decision engine rules, and safety policies from `[[AGENTS.md]]`.

## 1. Purpose & Inheritance
- Common operational parent for all child agent profiles (`antigravity.md`, `codex.md`, `claude.md`, `opencode.md`, `pi.md`).
- Enforces the **Live Verification Decision Engine** and 4-tier Confidence Ratings across all AI models.

## 2. Operational Initialization & Decision Pipeline
Upon booting, The AI Agent must:
1. Load `[[AGENTS.md]]` at repository root.
2. Load `[[base-agent.md]]`.
3. Search vault knowledge and evaluate confidence (`VERIFIED`, `HIGH`, `MEDIUM`, `LOW`).
4. If confidence is `MEDIUM` or `LOW`, recommend read-only Live Verification using available connection profiles in `00_meta/05_connections/`.
