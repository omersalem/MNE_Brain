---
runbook_id: "p2-fortigate-readonly-pilot"
title: "P2 FortiGate Edge Read-Only Pilot"
version: "1.7.0"
status: "operationally_reviewed"
runbook_type: "verification_pilot"
scope_categories: ["network"]
scope_services: ["firewall", "routing", "ssl-vpn", "nat"]
scope_entity_ids: ["fw-fortigate-edge-01"]
category_fallback_allowed: false
owner_team: "MNE-BRAIN-OWNER"
requires_exact_target: true
live_access_allowed: false
remediation_allowed: false
evidence_objectives: ["collect-target-reachability", "collect-network-path-state"]
stop_conditions: ["P0 containment validation fails", "Live policy is disabled or the owner has not explicitly said proceed for this exact read-only scope", "Target or check scope is not exact", "Evidence is stale, simulated, malformed, or cross-target", "A configuration change or remediation is proposed without explicit owner instruction"]
source_basis: "owner_review"
review_sources: ["MNE_INFRASTRUCTURE_MASTER_GUIDE.md", "dns-fortigate-vpn.md"]
operational_boundary: "PROCEDURE_REVIEWED_LIVE_STATE_UNVERIFIED"
last_reviewed: "2026-08-16"
---

# P2 FortiGate Read-Only Pilot Runbook

## Current authorization state

`P3_P4_SESSION_COMPLETE_POLICY_DISABLED`

The owner-approved two-check `get system status` and `get system interface physical` session completed successfully through the pinned MNE_Brain adapter and flowed in memory through P3 and P4. The policy was disabled immediately afterward. Do not run another check until the owner explicitly says `proceed` for the bounded read-only scope.

## Pilot scope

| Field | Required value |
|---|---|
| Profile | `fortigate_edge` |
| Adapter | `fortigate_ssh_readonly` |
| Canonical entity | `fw-fortigate-edge-01` (`172.23.70.4`) |
| Allowed checks | `system_status`, `interface_stats` |
| Maximum checks per request | 2 |
| Maximum timeout | 15 seconds |
| Maximum output | 65,536 bytes per check |
| Evidence freshness | 900 seconds maximum |
| Persistence | Disabled |
| Remediation | Disabled |

The operator selected `172.23.70.4`, and the canonical entity resolves that address exactly. Operators must not substitute another IP address, hostname, branch, or device at runtime.

## Owner-controlled command allowlist

These commands are candidates for owner review because they are declared in `profiles/fortigate_edge.yaml`:

```text
get system status
get system interface physical
```

Owner `proceed` applies to the exact command string. Additional arguments, pipes, redirection, command chaining, shell syntax, configuration mode, and diagnostic commands require a new explicit owner instruction.

## Entry checklist

- [x] Simplified P0 Git containment validated; local `.env` files are ignored.
- [x] Sole owner recorded as `MNE-BRAIN-OWNER`.
- [x] Two-check troubleshooting session authorized on 2026-08-16.
- [x] Current source workstation authorized for the bounded session.
- [x] Canonical management target confirmed as `fw-fortigate-edge-01` / `172.23.70.4`.
- [x] TCP/22 and authenticated read-only path validated with a pinned host key.
- [x] Existing `adminread` account authenticated for the owner-instructed read.
- [x] Credential reference provided through the ignored local `.env` file without duplicating the password.
- [x] The owner explicitly said `proceed`; both commands completed in one bounded P2 to P3 to P4 session.
- [x] Evidence retention is `NONE` and audit mode is `IN_MEMORY_ONLY`.
- [x] Stop conditions are controlled by `MNE-BRAIN-OWNER`.

## Stop conditions

Stop immediately and return a fail-closed result when any of these occurs:

- target differs from `fw-fortigate-edge-01` / `172.23.70.4`;
- management address cannot be resolved from one exact canonical entity;
- credential reference is missing, malformed, or resolves to an unexpected identity;
- host key or endpoint identity cannot be verified;
- command differs from the exact profile allowlist;
- authentication requests elevated or write-capable access;
- timeout or cancellation occurs;
- output exceeds 65,536 bytes;
- output contains unexpected binary/control content;
- transport result lacks connection attestation;
- evidence timestamp, expiry, target, check ID, or outcome is incomplete;
- any component proposes a configuration change or remediation.

## Controlled execution sequence after owner `proceed`

1. Record the sole owner's explicit `proceed`, scope reference, observation window, and correlation ID.
2. Confirm `MNE-BRAIN-OWNER` explicitly said `proceed` and repository policy was deliberately enabled; never override it at runtime.
3. Resolve the canonical entity to exactly one management target.
4. Resolve the credential reference from the ignored local environment without logging its value.
5. Validate endpoint identity and read-only account privilege.
6. Run one check, beginning with `system_status`.
7. Enforce timeout, output-size, cancellation, and redaction boundaries.
8. Verify the evidence record contains target, check ID, success outcome, UTC observation time, expiry, evidence ID, scope reference, and hashes.
9. Return the evidence to the investigation pipeline without persisting it.
10. Review the result before considering the second check.
11. End the session. Do not enter configuration mode or execute remediation.

## Evidence acceptance

Accepted evidence must satisfy `00_meta/schemas/live-evidence.schema.json`. A ping, open port, authenticated banner, documentation note, fixture result, or operator statement alone is not Level-5 evidence.

Simulation output always remains:

```text
evidence_status: simulated
trust_level: 0
connection_attempted: false
```

## Result handling

| Result | Required response |
|---|---|
| `SUCCESS` | Use only the attributed, unexpired evidence for a bounded answer |
| `PARTIAL` | Use successful evidence only; explicitly list failed checks |
| `TIMEOUT` or `FAILED` | Return insufficient evidence and the bounded failure code |
| `CANCELLED` | Return no new conclusion |
| `SCOPE_BLOCKED` | Request corrected authorization; do not retry another target |
| `NOT_CONFIGURED` | Keep live verification disabled |
| `SIMULATED_NOT_ACCEPTED` | Use for software validation only; never operational reasoning |

## Expansion rule

Do not expand to Cisco, VMware, another FortiGate, a branch, an alert gateway, persistence, or remediation without a new explicit instruction from `MNE-BRAIN-OWNER`. No signature, ticket, or additional approval reference is required.
