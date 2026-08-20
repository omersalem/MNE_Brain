# P2 Controlled Read-Only Operationalization Plan

## Objective

P2 turns the verified offline foundation into a controlled read-only operational capability. It does not authorize configuration changes, autonomous remediation, credential migration, or unrestricted infrastructure access.

## Authority boundary

The sole owner selected the simplified P0 Git-containment model. Local secrets may remain in ignored `.env` files. P2 implementation remains divided into offline work and owner-controlled live activation:

| Workstream | Repository implementation | Live activation |
|---|---|---|
| P2A governance, CI, contracts, fixtures, and runbooks | Authorized now | Not applicable |
| P2B read-only adapter and evidence pipeline | Implement and test with injected offline transport fixtures | Blocked until the exact target is selected and `MNE-BRAIN-OWNER` explicitly says `proceed` |
| P2C Ministry-domain operational pilot | Implement scenarios, metrics, reports, and acceptance logic offline | Blocked until the owner explicitly authorizes the exact bounded scope |

## P2A — Engineering readiness

1. Withdraw unsupported production-readiness claims.
2. Mark every test `offline`, `integration`, `live`, or `mutating`.
3. Run the complete safe collection in CI without credentials or network access.
4. Define read-only adapter, evidence, cancellation, timeout, output-size, and redaction contracts.
5. Use entity IDs as scope anchors; do not accept arbitrary user-supplied endpoints.
6. Load credentials or references from the ignored local environment. Credential values never enter plans, results, logs, evidence, or prompts.

## P2B — Read-only adapter boundary

The first adapter contract is FortiGate SSH read-only because the existing knowledge and profile layers already define bounded FortiGate checks. The repository implementation must:

- remain disabled in `config/p2_readonly_policy.yaml`;
- allow only named profiles, entity IDs, and check IDs;
- accept only exact commands declared in schema-valid profiles;
- require explicit policy authorization and a scope reference;
- require a credential reference supplied through the ignored local environment;
- impose check-count, timeout, and output-size budgets;
- support cancellation between checks;
- redact credential-like material before evidence construction;
- expose command and content fingerprints, never raw commands or transport output;
- create Level-5 evidence only after a successful, attributable transport result;
- persist nothing by default.

## P2C — Operational pilot

Offline pilot scenarios cover:

1. successful system-status evidence normalization;
2. attributable interface-down evidence and bounded reasoning;
3. transport timeout;
4. missing authorization;
5. out-of-scope target;
6. oversized output;
7. cancellation;
8. malformed transport response;
9. secret redaction;
10. expired evidence rejection;
11. unknown-target clarification.

Pilot metrics include routing latency, evidence collection duration, accepted evidence count, clarification state, reasoning state, answer status, redaction outcome, and connection-attempt truthfulness.

## Live entry criteria

No P2 live activation is permitted until these minimal safety criteria are satisfied:

- the 5/5 simple P0 containment validator continues to pass;
- `.env` and local credential files remain ignored and untracked;
- named target entity and management path selected by `MNE-BRAIN-OWNER`;
- read-only service account and credential reference provisioned through ignored local configuration;
- command allowlist accepted by `MNE-BRAIN-OWNER` through explicit `proceed`;
- maintenance or observation window recorded;
- network source, destination, port, and jump-host path explicitly scoped;
- cancellation and timeout are bounded, while audit stays `IN_MEMORY_ONLY` and retention stays `NONE`;
- `MNE-BRAIN-OWNER` explicitly says `proceed`;
- rollback is not applicable because the pilot is read-only.

## P2 completion criteria

P2 is complete only after both repository and controlled-pilot criteria pass:

- all offline CI and P2 tests pass;
- 100% of accepted live evidence has target, check ID, successful outcome, timestamp, expiry, and evidence ID;
- zero unsupported health, root-cause, or remediation claims;
- zero credentials, commands, or raw transport output in returned results and logs;
- every timeout, cancellation, authorization failure, scope failure, parse failure, and connection failure fails closed;
- the exact pilot scope was explicitly instructed by `MNE-BRAIN-OWNER`;
- remediation remains planning-only.
