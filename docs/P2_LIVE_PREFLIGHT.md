# P2 Live Pilot Preflight

**State:** System and physical-interface pilots completed successfully; one-shot policy disabled afterward.

Run:

```powershell
python -B scripts/preflight_p2_live_pilot.py
```

The preflight checks P0 containment, exact repository scope, canonical target resolution, target confirmation, local `.env` credential configuration, the fixed owner plus explicit `proceed` authorization, registered adapter scope, and live-policy activation. It never returns credential values and contains no network or process transport.

## Current blockers

- Repository live policy is disabled after the successful one-command pilot. Fresh authorization is required for another check.

The manual baseline and two project-integrated pilots were completed on 2026-08-16. Results are recorded in `P2_FIRST_LIVE_READ_REPORT.md` and `P2_INTERFACE_LIVE_READ_REPORT.md`.

## Confirmed target

The operator selected `172.23.70.4` on 2026-08-16. It resolves exactly to `fw-fortigate-edge-01`, the edge firewall and SSL-VPN gateway documented by the Ministry access baseline. The decision is recorded as `USER-CONFIRMED-EDGE-2026-08-16`.

A dedicated `fortigate_edge` profile now scopes the pilot to this device. The separate `fortigate` profile for `fw-fortigate-hq-01` remains unchanged and is not permitted by the pilot policy.

## Simple local credential setup

The ignored Release 2 `.env` now contains a local credential reference and the pinned SSH host key. It points to the existing ignored MNE credential source, so the password is not duplicated. Do not place the value in `.env.example`, tracked YAML, documentation, logs, or test fixtures.

P0 completion does not authorize the pilot. Policy may change to `OWNER_AUTHORIZED_LIVE_PILOT` only after exact target confirmation, command allowlist review, and `MNE-BRAIN-OWNER` explicitly saying `proceed`. No department, second approver, ticket, signature, or separate approval reference is required.
