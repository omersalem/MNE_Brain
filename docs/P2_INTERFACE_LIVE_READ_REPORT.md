# P2 FortiGate Physical-Interface Live Read Report

**Date:** 2026-08-16  
**Result:** Project-integrated read-only check succeeded; one-shot policy disabled afterward.

## Authorized scope

- Target entity: `fw-fortigate-edge-01`
- Target address: `172.23.70.4:22`
- Check ID: `interface_stats`
- Exact command: `get system interface physical`
- Owner authorization: `MNE-BRAIN-OWNER` explicitly said `proceed` for the bounded read-only check.
- Adapter reference: `PINNED-PLINK-FORTIGATE-EDGE-V1`
- Remediation or configuration commands: none

## Accepted evidence

- Status: `SUCCESS`
- Evidence ID: `ev-live-da0888f2f23b5243`
- Evidence status: `live_verified`
- Trust level: `5`
- Observed: `2026-08-16T07:31:33.686162+00:00`
- Expired: `2026-08-16T07:46:33.686162+00:00`
- Content SHA-256: `47c083a369a0f6efc4252cc26d7547e7019e122dd62021b8597c4bfd7eb1670c`
- Checks attempted/succeeded: `1/1`
- Connection attempted: yes
- Raw output returned: no
- Credential returned: no
- Persistence: not requested
- Failures: none

## Minimized interface summary

- Physical interface sections: `35`
- Interfaces reporting `up`: `6`
- Interfaces reporting `down`: `29`
- Evidence content size: `4,365` characters / `283` lines

This describes observed interface state only. It does not prove that any down interface is faulty because unused, disabled, or standby ports may legitimately report down. Fault identification requires correlation with the documented topology and the specific service or incident being investigated.

No interface names, addresses, raw telemetry, credentials, configuration changes, persistence, knowledge promotion, or remediation were returned by the live runner.
