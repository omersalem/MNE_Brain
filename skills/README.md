# Ministry Infrastructure Brain — Repository Skills Directory

## Overview
This directory contains project-specific, model-agnostic **Skills** that define specialized operational capabilities for the Ministry Infrastructure Brain repository.

These Skills:
- Belong **exclusively to this repository** (`d:\projects\MNE_Brain\MNE_Brain`).
- Extend `[[AGENTS.md]]` and `[[base-agent.md]]`.
- Are completely **AI-platform independent** (work seamlessly with Antigravity, Codex, Claude, OpenCode, ChatGPT, Pi, or future AI models).

---

## 🔍 Skill Discovery Protocol for AI Agents
Every AI Agent entering this repository MUST follow the automatic skill discovery sequence:

```
1. Read AGENTS.md ──> 2. Read base-agent.md ──> 3. Discover skills/ ──> 4. Auto-Select Applicable Skill
```

The user should NOT have to explicitly request a skill every time. The AI Agent must automatically detect when one of the project skills is applicable to the user's intent.

---

## 🛠️ The 4 Project Skills

| Skill Name | Directory | Primary Purpose | Trigger Conditions |
| :--- | :--- | :--- | :--- |
| **`discover`** | `skills/discover/skill.md` | Ingest, enrich, and update Digital Twin knowledge | Importing docs, onboarding new tech, updating notes |
| **`search`** | `skills/search/skill.md` | Search across all notes, profiles, runbooks & graph links | Querying entity facts, searching IPs, finding configs |
| **`explain`** | `skills/explain/skill.md` | Explain infrastructure topology, paths & dependencies | Asking how X works, explaining traffic flows, root causes |
| **`review`** | `skills/review/skill.md` | Audit vault quality, health, orphans & broken links | Auditing vault health, checking broken Wiki links, SPOFs |

---

## 🔒 Governance & Rule Inheritance
All Skills inherit 100% of their governance, read-only safety, markdown standards, and graph rules from `[[AGENTS.md]]`. Skills describe specific workflow procedures; `AGENTS.md` defines behavior and rules.
