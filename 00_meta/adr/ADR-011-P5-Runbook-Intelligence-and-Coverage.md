# ADR-011: P5 Runbook Intelligence and Coverage

**Status:** Accepted and sole-owner reviewed  
**Date:** 2026-08-16

## Context

P4 produces a professional case packet, but the repository has no governed mechanism for selecting the most relevant troubleshooting runbook or measuring coverage across all canonical entities. Returning arbitrary Markdown would increase context, leak obsolete instructions, and blur the difference between an offline-tested process and an operationally approved procedure.

## Decision

Introduce a schema-governed runbook registry that:

- validates unique IDs, lifecycle status, scope, owner, evidence objectives, and stop conditions;
- selects at most three candidates using exact entity, service, and category metadata;
- returns metadata only, never runbook body, commands, addresses, credentials, or raw output;
- labels reviewed procedures separately from current live-state verification;
- measures context coverage and operational coverage separately for every canonical entity;
- integrates bounded guidance into P4 handoff packets without executing or persisting anything.

Promotion to `operationally_reviewed` requires an explicit instruction from `MNE-BRAIN-OWNER` and is never automatic. The owner's 2026-08-16 instruction to complete all P5 authorized review of the complete phase. Twelve runbooks now carry the fixed owner-review boundary, including a dedicated Cisco FMC/FTD procedure.

## Consequences

The AI receives smaller, more relevant troubleshooting guidance and coverage gaps become measurable. The project can claim 46/46 reviewed procedure coverage, but not device health, current live state, production readiness, live access authorization, or remediation authority.
