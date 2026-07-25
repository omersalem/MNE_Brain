# AI Agents Architecture & Inheritance Framework

## Overview
The `agents/` directory defines the model-agnostic agent framework for the Ministry Infrastructure Brain. It enables multiple AI agents to collaborate on the single repository while sharing unified principles, governance, and safety rules.

---

## 🏗️ Inheritance Architecture

```
                       ┌───────────────────────────────┐
                       │           AGENTS.md           │
                       │ (Supreme Repository Standard) │
                       └───────────────┬───────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │      agents/base-agent.md     │
                       │   (Common Parent Template)    │
                       └───────────────┬───────────────┘
                                       │
         ┌─────────────────┬───────────┼───────────┬─────────────────┐
         ▼                 ▼           ▼           ▼                 ▼
  antigravity.md       codex.md    claude.md   opencode.md         pi.md
```

1. **`AGENTS.md` (Root Constitution):** Governs all repository standards, read-only safety, markdown rules, and domain models.
2. **`base-agent.md` (Parent Class):** Defines shared inheritance logic, task workflows, and extension mechanisms.
3. **Specific Agent Profiles (`*.md`):** Contains model-specific tool execution or prompt overrides without duplicating `AGENTS.md`.

---

## ➕ Adding New AI Agents
To introduce a new AI agent:
1. Create a new markdown file: `agents/<agent-name>.md`.
2. Inherit governance from `AGENTS.md` and lifecycle rules from `base-agent.md`.
3. Document only agent-specific tool bindings or platform quirks.
4. Do NOT duplicate rules from `AGENTS.md`.

---

## 🔍 How AI Agents Locate Instructions
When any AI Agent boots:
1. Read `AGENTS.md` at root.
2. Read `agents/base-agent.md`.
3. Read its specific profile file in `agents/<agent-name>.md`.
