# P11 Validation Report

- Date: 2026-08-31
- Offline full pytest: 246/246 passed
- OpenCode focused/runtime and security follow-up: 9/9 passed
- Codex App Server security tests: 7/7 passed
- P11 offline pilot: 20/20 passed; live connections 0; writes 0
- P10 regression pilot: 23/23 passed; live connections 0
- Architecture contracts: 57/57 passed, including 37 required schemas
- Master validation: 22/22 passed
- GUI syntax: 11/11 modules passed
- Python syntax: Codex bridge, OpenCode runtime/relay, conversation engine, API server, and provider registry passed
- Git patch integrity: passed

Coverage includes password hashing, failure lockout, logout revocation, API authentication, Codex App Server lifecycle, OpenCode catalog/auth/model classification and explicit pinning, child-environment isolation, SSRF/custom-provider validation, supervised turn/cancel/failure behavior, governed MCP routing, legacy conversation migration, sanitized workspace reads, a visible redacted operational trace, complete immutable P10 previews, one exact approval per displayed write batch, separately approved committed rollback, truthful P10 disabled-live-driver state, reconnect-safe SSE, CSRF/session/nonce/origin/loopback protection, export/import, accessibility, and presentation-only JavaScript.

The OpenCode lifecycle smoke started installed version 1.15.3 on authenticated loopback, discovered 212 providers and 7,501 models with two connected providers, reported native shell and edits denied, returned no secrets, and shut down without leaving a server process. It did not submit a provider prompt or access Ministry infrastructure. Earlier Codex/P7 acceptance remains documented separately. No infrastructure write was attempted, and this report does not establish general production readiness or current Ministry health.
