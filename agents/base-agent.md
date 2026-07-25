# Base AI Agent Operational Parent (`base-agent.md`)

> **Inheritance Notice:** This document is the secondary parent specification for all AI Agents. It inherits 100% of its governance, 3-Layer Architecture, Information Gain Decision Engine, and safety policies from `[[AGENTS.md]]`.

## 1. Purpose & Inheritance
- Common operational parent for all child agent profiles (`antigravity.md`, `codex.md`, `claude.md`, `opencode.md`, `pi.md`).
- Enforces maximum Information Gain per unit of Operational Cost before executing Live Discovery.

## 2. Information Gain Protocol
Upon entering Investigation Mode, The AI Agent must:
1. Measure Current Uncertainty and rank Hypotheses by probability.
2. Calculate Expected Information Gain vs. Operational Cost for candidate verification actions.
3. Select the Single Highest-Value Action that eliminates the most uncertainty with the lowest cost.
4. Present the standardized **Information Gain Verification Plan** format with explicit Stop Conditions.
5. Stop immediately once the primary hypothesis is confirmed or competing hypotheses are eliminated.
