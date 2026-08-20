# ADR-004: Dedicated Policy Engine Layer

> **Status:** APPROVED  
> **Date:** August 1, 2026  
> **Decision Makers:** Lead Software Architect & Chief AI Systems Architect  

---

## Context
In AI system design, combining policy evaluation (safety rules, read-only checks, risk levels) directly inside LLM reasoning prompts makes system safety non-deterministic and difficult to audit.

## Decision
We decided to introduce a dedicated, deterministic **Policy Engine Layer (`core/policy/`)** positioned between the Reasoning Engine and Execution:
```
Reasoning Engine ➔ POLICY ENGINE ➔ Execution / Live Verification
```
The Policy Engine evaluates verification necessity, read-only policy, Level 0–4 risk thresholds, and operational constraints using deterministic code rules without consuming LLM tokens.

## Consequences
* **Positive:** Guaranteed policy enforcement independent of LLM behavior.
* **Positive:** 100% auditable risk decisions.
* **Positive:** Decouples safety logic from prompt engineering.
