# P2 Offline Pilot Report

**Date:** 2026-08-15  
**Scope:** Repository-only controlled read-only operationalization  
**Result:** Passed offline acceptance; live activation not attempted and not authorized

## Acceptance result

| Acceptance area | Result |
|---|---|
| Policy remains disabled in the repository | Passed |
| Disabled-policy and direct-adapter bypass prevention | Passed |
| Canonical entity, profile, adapter, and check allowlisting | Passed |
| Opaque credential references and result minimization | Passed |
| No built-in network, process, or vendor transport | Passed |
| CI, readiness truthfulness, and operator stop conditions | Passed |

The injected-fixture pilot passed all 11 scenarios: simulation trust isolation, simulated-incident reasoning isolation, timeout, missing authorization, scope enforcement, output-size enforcement, cancellation, malformed transport result, redaction and result minimization, freshness enforcement, and unknown-target clarification.

## Safety evidence

- Live connections attempted: **0**
- Accepted live evidence records: **0**
- Simulation evidence trust level: **0**
- Repository live policy: **disabled**
- Built-in transport implementations: **0**
- Remediation actions attempted: **0**

No test result in this report establishes device health, Ministry reachability, credential validity, or production readiness.

The transport statements above describe the 2026-08-15 offline baseline. A separately scoped pinned Plink adapter was subsequently implemented and completed its first one-command live pilot on 2026-08-16; see `P2_FIRST_LIVE_READ_REPORT.md`.

## Regression evidence

- Master validation gates at P2 acceptance: **15/15 passed**; subsequently extended by P3
- Evidence-flow and benchmark scenarios: **11/11 passed**
- Classified pytest suite at P2 acceptance: **22/22 passed**; subsequently extended by P3
- P2 fixture scenarios: **11/11 passed**
- Scale checks: 1,000-note indexing and 50-way concurrent routing passed

## Remaining live gates

Simplified P0 Git containment and the first exact-target `system_status` pilot are complete. Any additional live activation remains blocked until the exact command scope is selected, `MNE-BRAIN-OWNER` explicitly says `proceed`, and policy is activated. The P0 validator must still pass at activation time.

The operator must use `intelligence/runbooks/p2-fortigate-readonly-pilot.md`. Any missing or mismatched gate is a stop condition and must result in `NOT_RUN` with no transport call.
