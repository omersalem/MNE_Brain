# P10 Safety Contract

## Governance

- `approval_state: OWNER_CONTROLLED`
- `owner_reference: MNE-BRAIN-OWNER`
- `audit_mode: IN_MEMORY_ONLY`
- `retention: NONE`
- Tickets, pages, notifications, assignments, and automatic remediation are disabled.

## Preparation

One exact active P7 binding, target, and identity pin are mandatory. Read-only evidence must be no older than five minutes, must match the binding and target, and must contain every required passing pre-check. Unknown fields, wrong parameter types, unsafe values, wildcard targets, dependency conflicts, unrelated pending changes, and unreviewed templates fail closed.

The core produces the exact vendor commands or typed API request and rollback, then binds `plan_id`, `plan_digest`, owner-session binding, `command_hash`, `rollback_hash`, `target_identity_hash`, risk, target, parameters, evidence state, intended changes, affected systems, dependencies, backup/snapshot claim, rollback conditions, failure conditions, and non-rollbackable operations into an integrity-protected in-memory plan. A structured catalog entry is not executable unless the live renderer can produce the exact wire operation.

## Approval

The exact phrase is case-sensitive, includes the complete plan digest, expires after five minutes, is accepted only from the authenticated loopback owner session, and is single-use. A Boolean owner flag is never approval. Any target, command, rollback, identity, risk, dependency, state, owner session, or plan mutation invalidates approval.

## Execution

Only one global execution may run. There are no wildcard or batch targets, automatic retries, hidden chains, unapproved follow-ups, downloaded scripts, or credential-bearing commands. Identity or state changes stop before submission. A timeout or uncertain outcome is `UNCERTAIN`. Independent read-only post-checks are required; driver exit status cannot establish success. Cancellation is accepted only before mutation; an in-flight action is reported as `MUTATION_ALREADY_STARTED`.

## Rollback

Rollback is generated before approval. The original single approval includes exactly that rollback only when the declared postcheck failure condition occurs. Its state is independently verified and it receives no automatic retry. A platform-native open transaction may still abort before commit. `NO SAFE ROLLBACK` is displayed when applicable.

## Live boundary

Unit and integration tests use mocks and do not open connections. Real transports are implemented but global execution remains disabled at rest. A live binding also requires a configured identity pin, a separate P10 write credential reference, a successful read-only privilege probe, fresh exact state evidence, and the per-plan owner approval. P7 read success never grants P10 write authority.
