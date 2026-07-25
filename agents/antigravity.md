# Antigravity AI Agent Profile

## 1. Purpose
Defines the platform execution profile for the Antigravity AI Agent.

## 2. Inheritance
This profile inherits 100% of its governance, engineering standards, workflows, and safety policies from:
- `[[AGENTS.md]]` (Highest Priority - Single Source of Truth)
- `[[base-agent.md]]` (Second Priority - Common Parent Specification)

## 3. Repository Initialization
Before performing any task, the AI Agent must always read:
1. `AGENTS.md`
2. `agents/base-agent.md`

## 4. Platform Notes
Available platform capabilities (e.g., subagents, workspace tools, terminal commands) may be utilized to execute tasks, provided they never violate the read-only safety, zero-duplication, or governance rules defined in `[[AGENTS.md]]`.

## 5. Conflict Resolution
If any conflict arises between documents:
1. `AGENTS.md` has **Highest Priority**.
2. `agents/base-agent.md` has **Second Priority**.
3. This profile document has **Lowest Priority**.
