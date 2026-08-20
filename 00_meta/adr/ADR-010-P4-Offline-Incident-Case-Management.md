# ADR-010: P4 Offline Incident Case Management

**Status:** Accepted for offline implementation  
**Date:** 2026-08-15

## Context

P3 can prepare a safe investigation, but professional incident response also needs explicit impact intake, provisional priority, ownership, continuation, check deduplication, and a consistent handoff. None of those should silently create an SLA, page a team, persist sensitive incident data, or convert reported impact into verified state.

## Decision

Add an offline case manager that wraps a P3 investigation and:

- accepts only schema-bounded operator-reported incident intake through a dedicated backend service and endpoint;
- captures target, symptom, affected service, branch/user scope, and availability;
- withholds evidence objectives until the target resolves exactly and impact is assessed;
- applies the single owner reference `MNE-BRAIN-OWNER` without department routing or notifications;
- exposes a schema-valid `OWNER_CONTROLLED` status with in-memory audit, no retention, and disabled automation;
- labels impact `REPORTED_NOT_VERIFIED` and priority `PROVISIONAL`;
- requires sole-owner priority confirmation;
- carries an in-memory timeline and reported check outcomes across a validated continuation;
- suppresses already collected or deliberately skipped objectives while retaining failed checks for review;
- emits a bounded handoff packet with no commands, raw output, credentials, IP addresses, or invented response target;
- performs no live access, external AI call, persistence, knowledge promotion, alerting, or remediation.

## Consequences

The owner receives a consistent intake form and case packet and avoids repeating work, while the system remains honest about impact, evidence, priority, audit, and retention. The GUI only serializes form values; all validation and readiness decisions remain in the backend. No additional approver, department, ticket, or signature is required. P4 does not establish an SLA or production readiness.
