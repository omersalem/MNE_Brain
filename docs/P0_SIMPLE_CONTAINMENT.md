# P0 Simple Local Secret Containment

**Date:** 2026-08-16  
**Scope:** Git containment only

The sole owner selected a simple credential model. Passwords, tokens, and other secrets may remain in local `.env` or ignored local credential files. No vault, rotation workflow, or complex migration is required by this P0 scope.

## Repository rules

- `.env` and `.env.*` are ignored.
- `.env.example` remains allowed and contains blank credential fields.
- Local token, key, credential, secret, PEM, and key files are ignored.
- CI fails if a local secret file becomes tracked or if credential fields in `.env.example` are populated.
- Validation never reads or prints local secret values.

## Boundary

This prevents accidental Git commits. It does not secure a compromised workstation, provide centralized credential management, rotate existing credentials, approve a live target, or authorize infrastructure access.

P2 live verification is disabled after the completed bounded sessions. Another session requires `MNE-BRAIN-OWNER` to explicitly say `proceed` while retaining the exact target, read-only credential reference, pinned adapter, and command allowlist.

## Validation result

On 2026-08-16, all 5 containment checks passed. The validator confirmed Git ignore behavior without reading or printing secret values.
