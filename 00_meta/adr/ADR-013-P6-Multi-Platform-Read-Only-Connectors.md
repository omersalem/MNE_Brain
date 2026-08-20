# ADR-013: P6 Multi-Platform Read-Only Connectors

**Status:** Accepted for offline implementation  
**Date:** 2026-08-16

## Context

P5 supplies reviewed troubleshooting procedures for all canonical entities, but only the FortiGate edge has a real, owner-gated transport. The remaining platform planners do not provide exact entity-to-connector routing or prove that their outputs can pass the common evidence boundary.

## Decision

Introduce one schema-governed P6 catalog and a minimal deterministic connector engine that:

- maps every canonical entity to exactly one platform connector;
- declares only bounded read-only checks and fingerprints operations in public plans;
- reuses the common injected `ReadOnlyVerificationAdapter` for normalization, redaction, budgets, cancellation, provenance, and trust handling;
- validates every entity through a non-connecting fixture that can produce only trust-0 simulated evidence;
- exposes catalog and coverage metadata without operations, credentials, addresses, or raw output;
- keeps live policy disabled and requires exact owner authorization, entity, checks, scope, opaque credential reference, and a registered transport before any future live read.

P6 contains no troubleshooting or remediation logic. The runbook and AI layers decide which evidence objective matters; connectors only collect and normalize an explicitly selected observation.

## Consequences

Offline connector planning and fixture coverage can reach 46/46 entities without claiming live readiness. Only the existing FortiGate edge transport is implemented for owner-gated live use; all other transports remain unregistered. Broad approval cannot activate a platform fleet, and fixture success cannot become verified evidence.
