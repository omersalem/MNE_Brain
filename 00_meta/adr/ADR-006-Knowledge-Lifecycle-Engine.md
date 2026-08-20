# ADR-006: Knowledge Lifecycle Engine & Two-Stage Promotion

> **Status:** APPROVED  
> **Date:** August 1, 2026  
> **Decision Makers:** Lead Software Architect & Chief AI Systems Architect  

---

## Context
Infrastructure telemetry is highly dynamic. Allowing live discovery runs to automatically overwrite permanent canonical notes in `knowledge/` introduces knowledge corruption when transient errors occur.

## Decision
We decided to introduce the **Knowledge Lifecycle Engine (`core/lifecycle/`)**:
* Compares live telemetry against Layer 1 facts to detect **Knowledge Drift**.
* Stages proposed updates in a human-in-the-loop **Review Queue**.
* Manages verification history, last verified timestamps, and knowledge freshness metrics.
* **Mandatory Constraint:** The system **NEVER automatically overwrites canonical knowledge**. Every update is traceable and evidence-backed.

## Consequences
* **Positive:** Prevents knowledge corruption from transient network outages.
* **Positive:** 100% auditable knowledge lineage.
* **Positive:** Clear separation of transient state (`operations/`) and canonical facts (`knowledge/`).
