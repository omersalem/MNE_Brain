# P11 Safety Contract

1. The primary server binds to loopback. Non-loopback mutation authority is rejected.
2. Every mutation requires the owner cookie, same-origin validation, matching CSRF token, inactivity validity, and a one-time nonce.
3. Wildcard CORS is absent and static files resolve only inside `gui/`.
4. Provider credentials remain server-side. OpenCode's generated Basic Auth password exists only in memory, and API keys/OAuth codes are forwarded only to authenticated loopback OpenCode. Responses, events, diagnostics, exports, logs, and tests contain no values or fragments.
5. Conversations, diagnostics, authorizations, approvals, tool calls, and workspace plans are in memory by default.
6. Provider choice cannot change authority. New GUI threads use loopback-authenticated `OWNER_FULL_CONTROL`; legacy modes remain import-compatible only.
7. External conversation turns always use a five-minute exact, single-use digest over sanitized context. The server automatically issues and consumes it for conversation and exact documented baseline context; supplied live evidence still requires explicit authorization. The explicit connection test sends only the fixed public prompt `hello`.
8. Safe provider failures expose a stable code, safe explanation, retryability, and diagnostic ID—not a response body, target, credential, or stack trace.
9. Models may propose tools. Deterministic server code validates the schema, immutable digest, permission, path, operation, approval, and state.
10. The repository root is discovered from the running checkout or worktree. Codex works in a per-thread sanitized mirror that excludes `.env`, `.git`, private keys, credential stores, symlinks, caches, and oversized files. Its allowlisted child environment contains no provider or device credential values. OpenCode native shell/edit/broad-read/web tools are denied; only the controlled MCP relay may reach the ToolBroker.
11. Workspace writes require an exact displayed diff, baseline digest, owner-session-bound exact phrase, single-use approval, immediate revalidation, post-apply verification, and zero automatic retries.
12. Workspace rollback is offered only while the verified post-apply digest is unchanged. It displays the reverse direction and needs a new exact, expiring, single-use approval.
13. P7 live reads remain globally disabled at rest. One exact server-prepared target/check/binding may be activated for five minutes only by the matching owner session, exact displayed phrase, and a single-use approval. Target or check drift, missing credentials, missing identity pins, expiry, replay, transport failure, or empty/rejected output produces no verified evidence and no automatic retry.
14. Infrastructure writes are impossible outside P10. P10 remains disabled at rest, risk-gated, owner-session-bound, single-use, no-retry, independently post-checked, and its one approval covers only the displayed declared-failure rollback.
15. The GUI renders server decisions and calculates no risk, command, digest, phrase, eligibility, or evidence truth.
16. No result becomes `LIVE_VERIFIED` without fresh attributable evidence containing exact target, check ID, successful outcome, observation time, source, and evidence ID.
17. Codex may not use shell commands to bypass infrastructure governance. Direct SSH, REST clients, WinRM, SNMP, database clients, and similar commands are declined. Only P7 can perform live reads and only P10 can perform infrastructure writes.
18. The GUI renders Codex/OpenCode text, progress, plans, command output, diffs, dynamic tool events, live non-secret provider/model metadata, approval requests, and terminal status. It does not decide what is safe or calculate approval content.
19. Every OpenCode turn carries the exact selected provider and model. A removed or disconnected model pauses the thread for explicit recovery; no silent fallback is permitted. Private reasoning is neither stored nor rendered.
20. Custom provider endpoints require reviewed HTTPS public origins or an explicitly approved true loopback endpoint. Credential-bearing URLs, private/reserved/link-local/metadata targets, unsafe schemes, query/fragment components, and sensitive custom headers fail closed.
