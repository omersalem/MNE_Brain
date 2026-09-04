# Owner Direct mode

`OWNER_DIRECT` is the primary interactive mode for the authenticated owner. It replaces P7/P10 as the normal operator path without deleting those legacy governed workflows.

## Discovery

One request addresses one exact canonical asset and one bounded read-only check. Registered SSH, PowerShell/WinRM, REST GET/HEAD, SNMP GET/WALK, HTTPS, and status adapters may run without a stored SSH, TLS, or SNMP pin. The adapter returns sanitized facts plus any observed host key, certificate fingerprint, serial, hostname, model, or version. The result is `IDENTITY_UNVERIFIED` unless it matches a supplied trusted identity; a difference is `IDENTITY_CONFLICT` and never changes a pin, binding, index, or canonical document. There is no range scan and no automatic retry.

Credentials are resolved only by the application credential loader. An adapter receives the opaque reference for its active connection; warning, evidence, audit, API, GUI, and conversation outputs never contain a credential value.

## Writes

An owner-specific request can prepare an exact device command or API operation outside the P10 template catalog. Preparation validates the canonical target and command-injection boundary, then displays target, exact change, operation, impact/downtime, blast radius, prechecks, postchecks, rollback or `NO_SAFE_ROLLBACK`, and identity status. `IDENTITY_CONFLICT` blocks a write; an owner may explicitly confirm an unverified identity after seeing the warning.

The GUI's **Final confirmation** sends the immutable operation once and runs the declared postcheck. It is not an approval phrase, a second approval, an automatic retry, or automatic rollback. A destructive action must originate in an explicit owner request and use that final confirmation immediately before execution.

## Identity audit

`POST /api/v2/owner-direct/identity-audit` accepts one exact discovery request per canonical asset. Each row contains the entity, address/host identity, platform and role, protocol/check, reachability/authentication/identity outcome, available serial/model/version, timestamp, evidence ID, and final status. The response includes a proposed enrollment/correction batch only; it never updates canonical material.

## API and engines

- `POST /api/v2/owner-direct/discover`
- `POST /api/v2/owner-direct/writes/prepare`
- `POST /api/v2/owner-direct/writes/{plan_id}/confirm`
- `POST /api/v2/owner-direct/identity-audit`

Codex App Server and OpenCode receive the same discovery, write-preparation, and audit tools. The final-confirmation endpoint is intentionally UI-owned and is not offered to either AI engine.
