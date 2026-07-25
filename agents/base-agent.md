# Base AI Agent Operational Parent (`base-agent.md`)

> **Inheritance Notice:** This document is the secondary parent specification for all AI Agents. It inherits 100% of its governance, 3-Layer Architecture, Investigation Planning Engine, and safety policies from `[[AGENTS.md]]`.

## 1. Purpose & Inheritance
- Common operational parent for all child agent profiles (`antigravity.md`, `codex.md`, `claude.md`, `opencode.md`, `pi.md`).
- Enforces minimum-device Investigation Planning before executing Live Discovery.

## 2. Investigation Planning Protocol
Upon entering Investigation Mode, The AI Agent must:
1. Determine Scope and Blast Radius to isolate affected vs. healthy systems.
2. Formulate and rank Hypotheses by probability.
3. Select the Minimum Devices Required (excluding healthy path hops).
4. Present the standardized **Investigation Plan** format with explicit reasoning and exit conditions.
5. Wait for approval before running read-only discovery connectors.
