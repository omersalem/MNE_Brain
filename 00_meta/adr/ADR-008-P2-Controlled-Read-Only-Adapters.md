# ADR-008: P2 Controlled Read-Only Adapter Boundary

## Status

Accepted for offline implementation on 2026-08-15. Live activation is disabled.

## Context

P1 established planning-only drivers and truthful non-execution states. P2 needs a path to attributable telemetry without allowing an adapter, profile, environment variable, or authorization boolean to bypass scope, credential, command, output, freshness, and persistence controls.

## Decision

- Live collection remains disabled by repository policy.
- Profiles identify targets by canonical entity ID, not arbitrary endpoints.
- Credentials are represented only by opaque references resolved outside MNE_Brain.
- Commands must exactly match a schema-valid profile and policy allowlist.
- A transport is dependency-injected; core code contains no socket, subprocess, SSH, or vendor SDK implementation.
- Successful transport output is bounded, redacted, hashed, normalized, and converted into expiring attributable evidence.
- Returned plans and results contain fingerprints but never commands, credentials, endpoints, or raw output.
- No evidence or audit persistence occurs unless `MNE-BRAIN-OWNER` explicitly requests it.
- Remediation remains unavailable.

## Consequences

Offline fixtures can validate the complete collection and evidence contract. Actual Ministry reachability and authentication remain untested until P0 is complete and `MNE-BRAIN-OWNER` explicitly says `proceed` for an exact read-only scope.
