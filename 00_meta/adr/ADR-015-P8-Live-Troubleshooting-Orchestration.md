# ADR-015: P8 Live Troubleshooting Orchestration

## Status

Accepted by `MNE-BRAIN-OWNER` for P8 implementation.

## Decision

P8 turns the P7 credentialed transport baseline into deterministic troubleshooting plans. A request must name one registered scenario and one exact active binding. A plan contains at most three read-only checks. The planner never connects; a separate local session may invoke only those exact P7 bindings after explicit owner `proceed`.

Operational bindings are reconciled to canonical entities with one of four dispositions: matched, update candidate, additional asset, or ambiguous. No disposition permits automatic canonical promotion.

Only fresh, attributable, scoped trust-level-5 evidence is accepted. The AI handoff is bounded to 6,000 characters and must reason only from accepted evidence. Reachability or a successful baseline alone cannot establish root cause.

## Safety consequences

- `approval_state: OWNER_CONTROLLED`
- `owner_reference: MNE-BRAIN-OWNER`
- `audit_mode: IN_MEMORY_ONLY`
- `retention: NONE`
- live access disabled at rest and after every scope
- no raw output in API or GUI
- no persistence, external AI call, notification, ticket, page, assignment, or remediation
- owner-excluded bindings are never retried

## Rejected alternatives

Automatic target promotion, broad multi-device collection, automatic remediation, and multi-approver workflow are outside this phase.
