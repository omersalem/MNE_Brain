# ADR-002: Brain-First Inside-Out Development Architecture

> **Status:** APPROVED  
> **Date:** August 1, 2026  
> **Decision Makers:** Lead Software Architect & Chief AI Systems Architect  

---

## Context
Traditional software refactoring often begins by reorganizing repository folders and file layouts for aesthetic reasons before building core features. This creates churn without functional validation.

## Decision
We decided to evolve Release 2 strictly from the **inside out** starting from the **Brain Core Engine**:
```
Architecture Contracts ➔ Core Flow ➔ Reasoning ➔ Policy ➔ Live Verification ➔ Knowledge Lifecycle ➔ Execution ➔ GUI
```
Repository folder refactoring is delayed and performed only when required by a specific architectural contract.

## Consequences
* **Positive:** Core reasoning and evidence-driven query resolution are validated before surrounding tooling is built.
* **Positive:** Eliminates aesthetic folder renaming churn.
* **Positive:** Ensures each milestone finishes in a working state.
