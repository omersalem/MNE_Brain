# AGENTS.md — Supreme Repository Governance & Single Source of Truth

> **Mandatory Rule:** This document is the single source of truth for all repository governance, standards, safety rules, and engineering philosophies. All AI Agents operating on this repository—regardless of AI model, platform, or interface—behave identically and inherit 100% of their rules from this file.

---

## 1. Governance & Core Philosophy
- **Model Independence:** AI models, tools, and platforms change; structured plain-text Markdown knowledge endures.
- **Read-Only Enforced:** Production infrastructure must never be modified by automated scripts or AI commands.
- **Preserve Human Notes:** Automated discovery and enrichment must never overwrite or delete human-authored notes.
- **Single Source of Truth:** All infrastructure facts must be maintained in canonical Markdown entity notes linked via Wiki links (`[[Entity-Basename]]`).

---

## 2. Unified Operational Workflows

### Unified Engineering & Cognitive Workflow
Every AI Agent follows the exact same 7-step execution pipeline:
```
1. UNDERSTAND ──> 2. ANALYZE ──> 3. PLAN ──> 4. VALIDATE ──> 5. EXECUTE ──> 6. REVIEW ──> 7. IMPROVE
```
1. **Understand:** Read prompt, search vault knowledge, clarify target scope.
2. **Analyze:** Inspect domain indices (`00_meta/04_indices/`), dependencies, and log histories.
3. **Plan:** Formulate action plan (or `implementation_plan.md` if complex).
4. **Validate:** Verify read-only safety, path parameters, and YAML frontmatter schemas.
5. **Execute:** Perform non-destructive tool calls, script updates, or note edits.
6. **Review:** Gather empirical evidence (test exit code 0) confirming success.
7. **Improve:** Evaluate if documentation should be enriched or if a new runbook/incident record is needed.

### Unified Discovery Workflow
- Apply 7-tier knowledge priority order (Vault Docs ➔ Diagrams ➔ Exported Configs ➔ Manuals ➔ Notes ➔ User Answers ➔ Read-Only Discovery).
- All live discovery must execute via the 11-stage universal discovery pipeline (`00_meta/framework/`).
- Present simple 4-option menus when asking the user for missing access parameters.

### Unified Documentation & Wiki Workflow
- Structure every note with YAML frontmatter demarcated by `---` matching `00_meta/02_schemas/tpl-*.md`.
- Form explicit bidirectional Wiki links: `[[Entity-Basename]]` (no file extensions or paths inside brackets).
- Preserve human-authored sections (`## Notes`, `## Custom Configurations`).

---

## 3. Read-Only Safety & Security Rules
- **STRICT PROHIBITION:** Never execute state-changing CLI/API commands (`set`, `config`, `commit`, `Remove-*`, `reboot`, `shutdown`).
- Mask passwords, tokens, and private keys in all logs and outputs.
- Highlight single points of failure (SPOFs) and critical redundancy risks in audit reports.
