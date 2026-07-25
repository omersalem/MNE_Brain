# Base AI Agent Operational Parent (`base-agent.md`)

> **Inheritance Notice:** This document is the secondary parent specification for all AI Agents. It inherits 100% of its governance, 3-Layer Architecture, Observation-Interpretation Framework, and safety policies from `[[AGENTS.md]]`.

## 1. Purpose & Inheritance
- Common operational parent for all child agent profiles (`antigravity.md`, `codex.md`, `claude.md`, `opencode.md`, `pi.md`).
- Strictly separates **Observations** (facts), **Interpretations** (hypotheses), **Verification** (actions), and **Conclusions** (verified decisions).

## 2. Observation & Language Protocol
Upon entering Investigation Mode, The AI Agent must:
1. List directly observed facts under *Observations*.
2. Formulate qualified engineering hypotheses under *Interpretations* using non-absolute language.
3. Classify blast radius into *Known Affected*, *Known Healthy*, and *Unknown*.
4. Execute Level 1/2 read-only verification actions to collect missing evidence.
5. Produce a *Conclusion* ONLY when supported by verified live telemetry.
