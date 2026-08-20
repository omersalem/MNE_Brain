# P2 First Authenticated Live Read Report

**Date:** 2026-08-16  
**Result:** Manual baseline and project-integrated read-only pilot succeeded.

## Authorized scope

- Target entity: `fw-fortigate-edge-01`
- Target address: `172.23.70.4:22`
- Account: existing read-only `adminread` account
- Command ID: `system_status`
- Exact command: `get system status`
- Owner authorization: `MNE-BRAIN-OWNER` explicitly said `proceed` for the bounded read-only check.
- Remediation or configuration commands: none

## Connection validation

- TCP/22 reachable from source `172.23.50.62`
- SSH host key type: ED25519
- Host key fingerprint pinned for the authenticated command: `SHA256:xhcU2OZV2xvdNcWtZ5LJv9/ZQs+qb+hsMIHHQjsJX+A`
- Authentication: succeeded
- Command exit code: `0`
- Credential printed or persisted by the command runner: no

## Minimized observed facts

- Hostname: `FG-MNE`
- Operation mode: `NAT`
- Current VDOM: `root`
- VDOM status: one VDOM in NAT mode
- HA mode: `standalone`
- Device-reported system time: `Sun Aug 16 10:17:17 2026`
- Last reboot reason: `warm reboot`

## Manual evidence boundary

- Manual evidence ID: `ev-manual-fortigate-edge-54279c925330e562`
- Minimized-content SHA-256: `54279c925330e562c17699003b1ee777abc68a17d6fa323c144b0cebc95ec6ef`
- Project evidence status: `MANUAL_LIVE_VALIDATION_NOT_ADMITTED`
- Project trust level: `0`

The manual connection and observed facts are live authenticated validation. That first result was not accepted into the MNE_Brain evidence pack because it ran outside the registered adapter boundary.

## Integrated MNE_Brain result

- Adapter reference: `PINNED-PLINK-FORTIGATE-EDGE-V1`
- Status: `SUCCESS`
- Evidence ID: `ev-live-e6fd44e7c2e996b4`
- Evidence status: `live_verified`
- Trust level: `5`
- Observed: `2026-08-16T07:25:08.014354+00:00`
- Expired: `2026-08-16T07:40:08.014354+00:00`
- Content SHA-256: `f81f9685f320c20b255705bfa340e1fe63e3395cae8f48f050a2d3038c603c02`
- Checks attempted/succeeded: `1/1`
- Connection attempted: yes
- Raw output returned: no
- Credential returned: no
- Persistence: not requested
- Failures: none

The accepted evidence existed only in memory and was bounded to a 900-second freshness window. No canonical knowledge was promoted, no raw output was persisted, and no remediation was attempted. The one-shot live policy was disabled immediately after success.

## Remaining project gates

1. Review the pilot evidence and adapter implementation.
2. Explicitly say `proceed` if another exact read-only check such as `interface_stats` is wanted.
3. Keep each new command separately scoped and disable policy after completion.
