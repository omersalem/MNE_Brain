# P11 Complete Conversation, Provider, Tool, and GUI Control Plane

## Outcome

P11 is complete as a schema-first control plane over P0-P10. It adds password-authenticated in-memory conversations and diagnostics, normalized providers, automatic sanitized-context handling, one GUI owner-autonomous mode, bounded automatic workspace/evidence/P7 reads, governed workspace and infrastructure write previews, verified workspace rollback, and a modern presentation-only GUI. P10 live drivers remain disabled at rest.

## Completed phases

| Phase | Implemented result |
|---|---|
| 0 — Architecture | ADR-018 preserves conversation, evidence, provider, permission, workspace, P7, P10, and presentation boundaries. |
| 1 — API containment | Password-authenticated single loopback owner cookie, login lockout, same-origin CSRF, inactivity expiry, one-time nonce, body/concurrency limits, and server-only credentials. |
| 2 — Contracts | Eleven strict P11 schemas, including workspace change and rollback plans. |
| 3 — Conversation | In-memory threads/turns/messages/events/diagnostics, search, compact stateless history, reconnect, cancellation, timeout, concurrency guard, and export/import. |
| 4 — Providers | Codex is primary. OpenCode is the complete secondary engine, with live provider/auth/model discovery, exact model pinning, normalized SSE, and safe failures. |
| 5 — External authorization | Exact five-minute digest over provider, model, prompt, sources, sanitized context, classification, and redaction; automatic for ordinary owner questions and registered read-tool results. |
| 6 — Tools | `OWNER_AUTONOMOUS` for new GUI threads with legacy modes import-compatible; protected automatic reads, exact diff or P10 preview approval, post-apply verification, and separately approved rollback. |
| 7 — GUI | Ten accessible responsive modules with owner login/logout, themes, safe errors/retry/copy, provider health, automatic-read progress, write previews, exact diffs, rollback, offline state, and import/export. |
| 8 — Validation | 246 tests, 57 architecture checks, 22 master gates, P10/P11 offline pilots, 11 GUI modules, security containment checks, live local OpenCode lifecycle smoke, and prior Codex/P7 acceptance checks. |

## Live boundary

- Deterministic local: validated offline.
- OpenCode: local server startup and health, dynamic provider/model discovery, authentication metadata, explicit model selection, cancellation, timeout, restart, governed MCP tools, and credential redaction are covered. Provider inference is never treated as Ministry live evidence.
- Ollama/local compatible: contract validated; service not live-tested.
- P7: exact registered read-only checks run automatically under the authenticated owner session; injected-transport behavior is validated and global unattended policy remains disabled at rest.
- P10: simulated coverage only; real execution disabled and not attempted.

No live provider result is Ministry infrastructure evidence. No step authorizes automatic remediation, persistent conversation storage, P7 bypass, or P10 bypass.
