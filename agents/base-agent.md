# Base AI Agent Operational Parent (`base-agent.md`)

> **Inheritance Notice:** This document is the secondary parent specification for all AI Agents. It inherits 100% of its governance, workflows, Intent-Based Mode Selection, and safety policies from `[[AGENTS.md]]`.

## 1. Purpose & Inheritance
- Common operational parent for all child agent profiles (`antigravity.md`, `codex.md`, `claude.md`, `opencode.md`, `pi.md`).
- Enforces Intent-Based Mode Selection across all 15 Core Intent classifications.

## 2. Intent Classification Protocol
Upon receiving a user prompt, The AI Agent must:
1. Classify prompt into one of 15 Core Intents (Learn, Explain, Search, Review, Troubleshoot, Investigate, Verify, Compare, Discover, Audit, Design, Plan, Implement, Optimize, Document).
2. If Intent is knowledge-focused ➔ Execute **Quick Mode** (fast, static KB search).
3. If Intent is production/troubleshooting-focused ➔ Execute **Investigation Mode** (methodical, read-only live verification recommendation + Verification Summary).
4. If Quick Mode confidence drops to `MEDIUM` or `LOW` ➔ Escalate to **Investigation Mode**.
