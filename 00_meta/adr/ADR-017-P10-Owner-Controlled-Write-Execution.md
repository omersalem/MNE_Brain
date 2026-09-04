# ADR-017: P10 Owner-Controlled Write Execution

## Status

Accepted for offline implementation on 2026-08-20. Live execution is not accepted or activated.

## Context

P0-P9 deliberately separate evidence collection, reasoning, remediation planning, execution, transports, and presentation. P10 must add controlled writes without turning an AI, alert, schedule, or Boolean flag into an approver.

## Decision

- The sole owner is `MNE-BRAIN-OWNER`; no ticket, department, second approver, notification, page, assignment, or retained audit is required.
- P10 uses schema-governed reviewed templates and exact structured platform transactions. User values are typed, allowlisted, escaped, and never interpolated into a general shell.
- A prepared plan is bound to one active P7 binding, one exact target, one identity pin, fresh read-only evidence, exact command and rollback hashes, and a five-minute expiry.
- Cataloged approval is `APPROVE <plan-id> <command-hash>`.
- Critical approval is `APPROVE CRITICAL <plan-id> <command-hash> I ACCEPT THE STATED RISKS`.
- Irreversible approval is `APPROVE IRREVERSIBLE <plan-id> <command-hash> I ACCEPT PERMANENT DATA OR SERVICE LOSS`.
- Level 4 becomes `CRITICAL_EXCEPTION_ONLY`; the legacy Boolean remediation path cannot execute it.
- Approval is local-interface-only, case-sensitive, single-use, replay-protected, and invalidated by any protected plan mutation.
- One global execution may run at a time, writes are never retried, uncertain outcomes require manual verification, and exit status alone cannot establish success.
- Committed rollback is a new prepared plan requiring a separate exact owner approval. Only a platform-native open transaction may abort automatically.
- All P10 audit and execution state is memory-only with no retention.
- The GUI is presentation-only. Core code owns schemas, rendering, risk, approval, and execution.

## Consequences

Offline injected-driver validation can establish deterministic safety behavior, not production readiness. A future live adapter requires a separate target-specific plan and the owner's exact action-level approval. No live device write is authorized by this ADR.
