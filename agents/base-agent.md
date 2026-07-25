# Base AI Agent Operational Parent (`base-agent.md`)

> **Inheritance Notice:** This document is the secondary parent specification for all AI Agents. It inherits 100% of its governance, 3-Layer Architecture, Golden Investigation Principle, Observation-Interpretation Framework, and safety policies from `[[AGENTS.md]]`.

## 1. Purpose & Inheritance
- Common operational parent for all child agent profiles (`antigravity.md`, `codex.md`, `claude.md`, `opencode.md`, `pi.md`).
- Enforces the **Golden Investigation Principle**: maximize information gain, minimize operational cost, prefer binary decisions, and stop immediately when uncertainty is reduced.
- Strictly separates **Observations** (facts), **Interpretations** (hypotheses), **Verification** (actions), and **Conclusions** (verified decisions).

## 2. Observation & Golden Investigation Protocol
Upon entering Investigation Mode, The AI Agent must:
1. Apply the **Golden Investigation Principle** to reduce uncertainty using the fewest, highest-value binary checks.
2. List directly observed facts under *Observations*.
3. Formulate qualified engineering hypotheses under *Interpretations* using non-absolute language.
4. Classify blast radius into *Known Affected*, *Known Healthy*, and *Unknown*.
5. Execute Level 1/2 read-only verification actions to collect missing evidence.
6. Stop immediately once sufficient evidence is obtained, producing a *Conclusion* strictly supported by verified telemetry.

