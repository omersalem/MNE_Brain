# Base AI Agent Operational Parent (`base-agent.md`)

> **Inheritance Notice:** This document is the secondary parent specification for all AI Agents. It inherits 100% of its governance, workflows, and safety rules from `[[AGENTS.md]]`.

## 1. Purpose & Inheritance
- Serves as the common operational parent for all child agent profiles (`antigravity.md`, `codex.md`, `claude.md`, `opencode.md`, `pi.md`).
- Ensures zero behavioral variance when switching between different AI models or platforms.

## 2. Operational Initialization
Upon booting, The AI Agent must:
1. Load `[[AGENTS.md]]` at repository root.
2. Load `[[base-agent.md]]`.
3. Execute the single unified 7-step engineering pipeline defined in `[[AGENTS.md]]`.
