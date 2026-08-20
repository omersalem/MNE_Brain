# ADR-012: P0 Simple Local Secret Containment

**Status:** Accepted  
**Date:** 2026-08-16

## Context

The operator explicitly requested a simple credential model: passwords and secrets may remain in a local `.env` file, provided that `.env` is ignored by the repository. A vault, credential rotation program, or complex migration is not required for this P0 scope.

## Decision

- Local `.env` and `.env.*` files are ignored by Git.
- `.env.example` remains commit-safe and contains blank credential values only.
- Local token, key, credential, secret, PEM, and key files are ignored.
- CI verifies ignore behavior and rejects tracked local secret files.
- Credential values are never printed by the validator.
- P0 completion does not enable live verification; exact target scope and explicit owner `proceed` remain separate requirements.

## Consequences

Local credentials can be configured simply without entering repository history. This protects against accidental commits but does not protect a compromised workstation, rotate credentials, provide centralized revocation, or establish production readiness.
