# P3/P4 Live-Evidence Session Report

**Date:** 2026-08-16  
**Target:** `fw-fortigate-edge-01` / `172.23.70.4`  
**Scope reference:** `P3-P4-LIVE-EVIDENCE-SESSION-2026-08-16`  
**Result:** Successful evidence transfer; no fault or root cause established

## P2 collection

The pinned `fortigate_ssh_readonly` adapter executed exactly two allowlisted commands. Both succeeded at trust level 5. No credential or raw device output was returned, and no evidence was persisted.

| Check | Evidence ID | Observed UTC | Expires UTC | Content SHA-256 |
|---|---|---|---|---|
| `system_status` | `ev-live-7080662f914746b5` | `2026-08-16T07:45:15.726076+00:00` | `2026-08-16T08:00:15.726076+00:00` | `f3e2d49899fe96200e92a8414ca20627613438aabfd7519a6082aca56ee1d209` |
| `interface_stats` | `ev-live-3a0bd9cefb33a3ee` | `2026-08-16T07:45:16.213755+00:00` | `2026-08-16T08:00:16.213755+00:00` | `47c083a369a0f6efc4252cc26d7547e7019e122dd62021b8597c4bfd7eb1670c` |

## P3 investigation

- Investigation: `inv-p3-66873e17b37b`
- Accepted evidence records: 2
- Status: `EVIDENCE_REQUIRED`
- Reasoning: `PENDING_EVIDENCE`
- Conclusive root cause: none
- Next objectives: target reachability, affected network path, and relevant dependency state

The interface inventory is accepted evidence but is not a diagnosis. Interface-down counts can include intentionally unused ports and require correlation to the affected service, flow, branch, or physical port.

## P4 case handoff

- Case: `case-p4-217a3a277530`
- State: `IMPACT_REQUIRED`
- Priority: `UNASSESSED`
- Suggested primary owner: Network & Security Operations Team
- Notification sent: no
- Persistence attempted: no
- Remediation attempted: no

No user impact was supplied, so the system correctly refused to invent a priority. The case and handoff existed only in memory.

## Closure state

The P2 policy was reset to `P3_P4_SESSION_COMPLETE_POLICY_DISABLED` immediately after collection. A repeat attempt returned `NOT_CONFIGURED`, executed zero checks, and reported `connection_attempted: false`. Another live session requires fresh authorization.
