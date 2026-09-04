# P10 Readiness

## Implemented

- Nine strict schemas with unknown-field rejection.
- Seven catalog families, 56 reviewed templates, 176 action variants, and eight real platform transport families.
- Exact vendor CLI, typed PowerShell, FMC REST, and vCenter REST rendering for 87 actions; 89 underspecified actions fail closed.
- Separate P7 read and P10 write credential references, exact target revalidation, SSH/TLS/Kerberos identity gates, no-retry submission, bounded output hashing, process abort where available, and independent exact state-query renderers.
- `GET /api/p10/readiness` and the GUI show per-platform targets, credential readiness, renderer coverage, and blockers without exposing secrets.
- Cataloged and controlled-expert critical/irreversible workflows. FMC-managed FTD changes are FMC-only.
- Five-minute expiry, session-bound complete-plan phrase, single-use approval, command/rollback/identity hashes, integrity checks, local-only source enforcement, CSRF, and replay protection. One approval covers only the displayed prechecks, change, postchecks, and declared-failure rollback.
- Global concurrency lock, zero write retries, cancellation before submission, fresh identity/state comparison, pending-change protection, bounded timeouts, uncertain-state handling, and independent post-checks.
- FortiGate conflict/dependency protection, BIG-IP transaction abort, FMC unrelated-deployment checks and REST-only managed-FTD boundary, typed PowerShell restrictions, VMware capacity checks, protected switch-uplink checks, and managed Linux operation restrictions.
- Presentation-only GUI and in-memory API state.

## Disabled at rest

- P10 execution at rest.
- Global P10 execution. Real transports exist but are unreachable while this switch is off.
- Automatic remediation, schedules, batches, retries, unplanned rollback, tickets, pages, notifications, and assignments.
- Persistent plans, results, approvals, audit, raw output, and credentials.

## Current external blockers

- No separate P10 write credential is configured for any binding; write authorization has therefore not been probed or assumed.
- Tulkarm switch target/identity is not configured, FMC SSH authentication failed, and vCenter REST lacks authorization in the 2026-08-27 read-only baseline.
- The first target-specific write test has intentionally not started. See `docs/P10_LIVE_EXECUTION_READINESS_REPORT.md`.
