# Base AI Agent Operational Parent (`base-agent.md`)

> **Inheritance Notice:** This document is the secondary parent specification for all AI Agents. It inherits 100% of its governance, 3-Layer Architecture, Evidence Ranking Engine, and safety policies from `[[AGENTS.md]]`.

## 1. Purpose & Inheritance
- Common operational parent for all child agent profiles (`antigravity.md`, `codex.md`, `claude.md`, `opencode.md`, `pi.md`).
- Enforces qualitative Evidence Ranking (`Primary`, `Secondary`, `Possible`, `Unlikely`, `Eliminated`) and rejects arbitrary numerical percentages.

## 2. Evidence Ranking Protocol
Upon entering Investigation Mode, The AI Agent must:
1. Construct the 5-element Evidence Model for each hypothesis (*Statement*, *Supporting*, *Contradicting*, *Missing*, *Confidence*).
2. Present the standardized **Hypothesis Evidence Matrix**.
3. Select the verification target that fills the single largest Missing Evidence gap with the lowest operational cost.
4. Update the evidence model continuously and stop once sufficient evidence is obtained.
