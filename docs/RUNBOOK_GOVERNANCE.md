# Runbook Governance

## Sole-owner model

`MNE-BRAIN-OWNER` is the only owner, operator, administrator, and approver. No department review, ticket, signature, second approver, or separate approval reference is required.

The lifecycle remains simple:

- `draft_unvalidated`: structured but not reviewed;
- `offline_validated`: repository contract tested;
- `operationally_reviewed`: the sole owner reviewed the procedure, scope, evidence objectives, and stop conditions.

The owner may explicitly instruct promotion of one runbook or an entire named phase. AI and tests must never promote a runbook without that explicit instruction. The 2026-08-16 instruction to finish all P5 authorized review and promotion of all 12 P5-governed procedures.

## Permanent boundary

Every reviewed procedure must keep:

- `owner_team: MNE-BRAIN-OWNER`;
- `source_basis: owner_review`;
- `operational_boundary: PROCEDURE_REVIEWED_LIVE_STATE_UNVERIFIED`;
- exact-target matching and attributable evidence objectives;
- read-only collection blocked until the owner explicitly says `proceed`;
- configuration and remediation blocked until separately instructed;
- live access, remediation, notifications, ticketing, paging, automatic assignment, automatic promotion, and persistence disabled.

`review_sources` records the technical documents used to assess procedure fit. It is traceability, not an approval mechanism.
