# Base AI Agent Operational Parent (`base-agent.md`)

> **Inheritance Notice:** This document is the secondary parent specification for all AI Agents. It inherits 100% of its governance, workflows, Dual Operating Modes, and safety policies from `[[AGENTS.md]]`.

## 1. Purpose & Inheritance
- Common operational parent for all child agent profiles (`antigravity.md`, `codex.md`, `claude.md`, `opencode.md`, `pi.md`).
- Enforces automatic selection between **Quick Mode** (Documentation) and **Investigation Mode** (Production) across all AI models.

## 2. Operational Initialization & Mode Selection
Upon booting, The AI Agent must:
1. Load `[[AGENTS.md]]` at repository root.
2. Load `[[base-agent.md]]`.
3. Assess user prompt intent:
   - If general inquiry or architecture lookup ➔ Execute **Quick Mode** (fast, concise, static KB search).
   - If troubleshooting, connectivity issue, or checking live status ➔ Execute **Investigation Mode** (methodical, evidence-based, read-only live verification recommendation + Verification Summary).
