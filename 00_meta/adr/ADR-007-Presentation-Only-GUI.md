# ADR-007: Presentation-Only GUI Rule (Zero Business Logic in UI)

> **Status:** APPROVED  
> **Date:** August 1, 2026  
> **Decision Makers:** Lead Software Architect & Chief AI Systems Architect  

---

## Context
Web dashboards often accumulate business logic, query routing, state management, and policy enforcement over time, leading to fragmented architecture and duplicate decision logic.

## Decision
We decided to enforce a strict architectural constraint: **The GUI must NEVER contain business logic.**
* The GUI is 100% responsible for presentation (rendering telemetry graphs, query responses, and investigation state).
* All query routing, entity resolution, reasoning, policy evaluation, live verification, and decision-making remain strictly inside `MNE_Brain`.

## Consequences
* **Positive:** MNE_Brain remains 100% functional via CLI, API, n8n, or GUI identically.
* **Positive:** Prevents UI code bloat and logic fragmentation.
* **Positive:** Simplifies frontend maintenance and testing.
