# P2 Readiness

**Current state:** Offline P2 implementation complete and accepted. Live activation blocked.

| Readiness item | State | Evidence or blocker |
|---|---|---|
| P1 offline foundation | Complete | Preserved by the current master gates, benchmarks, and classified pytest collection |
| Test classification | Implemented | Default CI selects only `offline` and safe `integration` markers |
| Unsupported production certificate | Withdrawn | `docs/PRODUCTION_HARDENING_REPORT.md` is an invalidation notice |
| P2 policy | Disabled after one-shot use | Integrated pilot succeeded; another live check requires `MNE-BRAIN-OWNER` to explicitly say `proceed` and activate the exact scope |
| Read-only adapter contract | Implemented and tested | Core remains transport-neutral; the explicit Plink integration pins the host key and exact target, identity, credential reference, and command |
| Live-evidence schema and normalizer | Implemented and tested offline | Attribution, freshness, redaction, output bounds, and target matching fail closed |
| FortiGate offline fixture pilot | Complete | 11/11 scenarios passed with injected fixtures, zero live connections, and zero accepted live evidence |
| P0 containment | Complete for owner-selected scope | 5/5 Git-containment checks pass; `.env` is ignored; no vault or credential rotation is required |
| Live-pilot preflight | Implemented | Non-connecting check reports exact blockers without returning credential values |
| Live target selection | Complete | Operator selected `fw-fortigate-edge-01` / `172.23.70.4`; dedicated profile and exact policy scope created |
| Manual authenticated baseline | Complete | TCP/22 reachable; pinned ED25519 host key; `get system status` authenticated successfully with the read-only account |
| Pilot authorization | Recorded for completed command | `MNE-BRAIN-OWNER` explicitly said `proceed`; it authorizes no additional command |
| Local credential configuration | Complete | Ignored v2 `.env` references the existing ignored local MNE credential source and pins the observed SSH host key; no password is duplicated or printed |
| Integrated transport | Complete for first scope | Pinned Plink adapter enforces exact target, entity, profile, check, command, credential reference, timeout, and host key |
| Integrated live pilot | Complete | One `system_status` check created accepted in-memory Level-5 evidence with no persistence, raw-output return, credential return, or remediation |
| Interface-status pilot | Complete | One `interface_stats` check created accepted in-memory Level-5 evidence covering 35 physical interface sections; 6 reported up and 29 down |
| Production readiness | Not established | No live pilot or operational sign-off |

Passing offline P2 tests must never change the final three states automatically. The repository portion of P2 is complete; P2 live activation and operational sign-off remain incomplete until every documented entry criterion is satisfied.
