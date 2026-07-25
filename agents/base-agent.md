# Base AI Agent Operational Parent (`base-agent.md`)

> **Inheritance Notice:** This document is the secondary parent specification for all AI Agents. It inherits 100% of its governance, 3-Layer Architecture, Layered Search Strategy, and safety policies from `[[AGENTS.md]]`.

## 1. Purpose & Inheritance
- Common operational parent for all child agent profiles (`antigravity.md`, `codex.md`, `claude.md`, `opencode.md`, `pi.md`).
- Enforces the 3-Layer Architecture (`knowledge/`, `operations/`, `intelligence/`) and Layered Search Strategy across all AI models.

## 2. Layered Search & Intent Protocol
Upon receiving a user prompt, The AI Agent must:
1. Classify prompt into one of 15 Core Intents.
2. Route search retrieval strictly through the appropriate layer order (`knowledge/`, `operations/`, `intelligence/`).
3. Maintain distinct operational memory: **Facts** in `knowledge/`, **History** in `operations/`, and **Experience** in `intelligence/`.
