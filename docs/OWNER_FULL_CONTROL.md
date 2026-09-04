# Owner Full Control — Operator Guide

`OWNER_FULL_CONTROL` is the loopback-only authenticated operating mode for the MNE_Brain console. It gives both Codex App Server and OpenCode the same governed capabilities: they can investigate documented infrastructure and request registered read-only checks automatically, but neither can receive a credential value, run unmanaged infrastructure tooling, or perform a write outside P10.

## What runs automatically

- Safe repository, documentation, and local reads.
- Registered P7 read-only checks when the authenticated owner session, exact entity, binding, target, credential reference, and identity pin are all available.
- Cross-platform evidence collection that returns normalized, attributed facts and evidence IDs only.
- Post-change validation after an approved P10 change.

The coverage endpoint, `GET /api/v2/owner-full-control/status`, enumerates every canonical asset. Each is `READY`, `IDENTITY_CONFLICT`, `CREDENTIAL_REFERENCE_MISSING`, `IDENTITY_PIN_MISSING`, `TRANSPORT_UNSUPPORTED`, or `OWNER_EXCLUDED`; no asset is silently omitted. Read results remain separately labelled `DOCUMENTED`, `REACHABLE`, `AUTHENTICATED`, `LIVE_VERIFIED`, `CONFLICT`, `FAILED`, or `NOT_RUN`.

## Credentials and identity

The loopback server resolves only opaque environment-reference names from ignored local `.env` files or an ignored external reference file selected by `MNE_CREDENTIAL_ENV_FILE` (the previous FortiGate-specific external file remains supported). It passes credentials directly to the transport at execution time. Temporary SSH credential files are scoped to the single transport invocation and removed immediately afterward.

The server returns only readiness states (`CONFIGURED`, `MISSING`, `INVALID`, or `AUTHENTICATION_FAILED`) and never returns a credential value, private key, token, command argument containing a secret, or raw secret-bearing transport output. Kerberos bindings use their registered FQDN; SSH and REST bindings use their registered exact target and identity pin. A documented or configured target conflict blocks live activity pending owner-reviewed authenticated identity proof.

## One approval for one immutable change batch

P10 must prepare a complete bundle before it can be approved. The GUI shows the exact target, identity proof, current-state evidence, operation bytes or typed API request, parameters, command hashes, risk, blast radius, possible downtime, dependencies, prechecks, success/failure conditions, postchecks, rollback, and non-rollbackable warning.

The exact case-sensitive approval phrase contains the complete plan digest. It is bound to the active loopback owner session, expires in five minutes, is single-use, and is replay-resistant. Any change to target, identity, command, parameter, evidence/state digest, dependency, risk, or rollback invalidates it.

That one approval covers only:

- the displayed prechecks;
- the displayed change operations;
- the displayed postchecks; and
- the displayed rollback when a declared postcheck failure condition occurs.

It never authorizes a new target, a follow-up command, a new parameter, a broader scope, or a rollback not included in the displayed plan. FTD changes must be prepared through FMC with the registered FMC REST path; direct managed-FTD configuration is rejected.

## Stop, recovery, and uncertainty

Use the **Cancel before mutation** control to cancel a prepared plan. Once mutation starts, the system reports `MUTATION_ALREADY_STARTED` instead of pretending it stopped the device action. P10 has bounded timeouts and no automatic retry. If the final state cannot be proven after a timeout, transport interruption, or ambiguous response, the result is `UNCERTAIN` and requires owner investigation.

After a declared failed postcheck, only the pre-approved rollback bundle may run automatically. Its result is independently revalidated against the prepared identity and state. A failed or unverified rollback is reported as `ROLLBACK_FAILED` or `UNCERTAIN`; it never triggers another automatic attempt.

## Enablement and remaining blockers

The server itself is loopback-only. P7 live reads and P10 writes remain disabled at rest by policy. To make an individual action possible, configure the matching ignored credential reference and pin, resolve any conflict with authenticated identity evidence, and use the displayed owner flow. Enabling a credential does not enable a write. Live infrastructure writes were not performed while implementing this feature.
