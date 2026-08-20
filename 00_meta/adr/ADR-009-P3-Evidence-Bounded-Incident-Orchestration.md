# ADR-009: P3 Evidence-Bounded Incident Orchestration

**Status:** Accepted for offline implementation  
**Date:** 2026-08-15

## Context

P1 established truthful retrieval and P2 established a fail-closed read-only adapter boundary. The API still assembled investigation components ad hoc, selected a default platform when none was resolved, and invoked a synthetic knowledge-drift comparison. That behavior is not suitable for dependable Ministry-wide troubleshooting.

## Decision

Introduce one offline incident orchestrator that:

- requires deterministic routing and an exact canonical target for target-dependent investigations;
- treats `related_entities` only as documented adjacency, never as live dependency health or causality;
- accepts live evidence only through the existing evidence-pack validation boundary;
- returns evidence objectives rather than commands;
- creates a compact, bounded AI handoff containing attribution, unknowns, and safety constraints;
- records timing and context-size metrics in memory;
- performs no live connection, external AI call, persistence, lifecycle promotion, or remediation.

The API delegates troubleshooting assembly to this orchestrator. It must not guess a platform or generate synthetic drift input.

## Consequences

Offline investigations become consistent, measurable, and safe across Ministry domains. They can identify the next evidence needed quickly, but they cannot establish present health or root cause without fresh attributable live evidence. P0 and P2 live-pilot gates remain unchanged.
