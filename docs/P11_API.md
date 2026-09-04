# P11 Local API

The primary server binds to loopback. `GET /api/v2/session` establishes an owner session. Every POST requires the owner cookie, matching same-origin `Origin`, `X-CSRF-Token`, and a unique `request_nonce`.

## Conversations

- `POST /api/v2/threads`
- `GET /api/v2/threads?search=`
- `GET /api/v2/threads/{thread_id}`
- `GET /api/v2/threads/{thread_id}/export`
- `POST /api/v2/threads/import`
- `POST /api/v2/threads/{thread_id}/turns`
- `GET /api/v2/turns/{turn_id}/events` (SSE with `Last-Event-ID` reconnect)
- `POST /api/v2/turns/{turn_id}/cancel`
- `POST /api/v2/threads/{thread_id}/engine`
- `POST /api/v2/threads/{thread_id}/permission`
- `GET /api/v2/codex/readiness`
- `GET /api/v2/opencode/readiness`
- `POST /api/v2/codex/approvals/{approval_id}/approve|deny`

Portable exports contain user-visible conversation data only. Credentials, owner sessions, external authorizations, raw diagnostics, and server audit state are excluded. Imports are schema-bounded, limited to 2 MB, and receive new in-memory IDs.

## Providers and diagnostics

The GUI exposes Codex and OpenCode AI engines. OpenCode owns the dynamic vendor/model catalog and provider connection mechanisms:

- `GET /api/v2/opencode/providers`
- `POST /api/v2/opencode/providers/refresh`
- `POST /api/v2/opencode/providers/connect-api`
- `POST /api/v2/opencode/providers/oauth/start`
- `POST /api/v2/opencode/providers/oauth/callback`
- `POST /api/v2/opencode/providers/disconnect`
- `POST /api/v2/opencode/providers/test`
- `POST /api/v2/opencode/custom-providers/save|remove`
- `POST /api/v2/opencode/restart`

API key and OAuth code fields are removed from the request object before results are constructed. Results contain only connection status, instructions, the exact provider authorization URL where applicable, and non-secret catalog metadata.

Legacy provider-profile routes remain for offline compatibility and diagnostics but are not additional GUI AI engines:

- `GET|POST /api/v2/providers`
- `POST /api/v2/providers/{provider_id}/enable|disable`
- `POST /api/v2/providers/{provider_id}/test` performs configuration validation only
- `POST /api/v2/providers/{provider_id}/connect` performs an explicit real network check with the fixed public prompt `hello`
- `POST /api/v2/credentials/{CREDENTIAL_REF}`
- `GET /api/v2/diagnostics/{diagnostic_id}`
- `GET /api/v2/settings`

Codex checks report binary discovery, ChatGPT authentication, App Server initialization, repository root, sandbox, approval policy, service tier, restart count, and non-secret P7/P10 readiness. OpenCode checks report binary/version, protected loopback health, restart count, connected-provider/model counts, and denied native shell/edit status. Neither returns a credential value.

## External conversation data

Ordinary external turns automatically prepare and consume a five-minute exact digest over provider, model, prompt, documented source set, sanitized context, classification, and redaction result. This removes the GUI popup without bypassing redaction or digest validation. `POST /api/v2/threads/{thread_id}/external-authorizations` remains available for explicit supplied-evidence flows; fresh live evidence is never auto-authorized. Each digest is single use. The fixed public provider connection check is not a conversation send and carries no conversation or Ministry evidence.

## Owner Direct API

New owner conversations default to `OWNER_DIRECT`. The server accepts authenticated, same-origin requests only:

- `POST /api/v2/owner-direct/discover` executes one exact registered read-only check and returns a sanitized evidence row. An absent pin is reported as unverified identity evidence, not a read block.
- `POST /api/v2/owner-direct/writes/prepare` returns the complete immutable plain-English risk warning and sends nothing.
- `POST /api/v2/owner-direct/writes/{plan_id}/confirm` is the one final UI confirmation; it sends the exact prepared operation once and returns postcheck status.
- `POST /api/v2/owner-direct/identity-audit` runs no more than one requested attempt per canonical asset and returns a proposed enrollment/correction batch without changing records.

The endpoints reject malformed operations, injection characters, secret-bearing operations, unknown assets, and noncanonical targets unless the owner explicitly identifies the exact new target in the request. API responses contain opaque credential status/references only, never values.

## Permission modes and tools

New GUI threads use `OWNER_DIRECT` with Codex App Server when it is ready or an explicitly selected OpenCode model. Legacy imports may retain older modes; engine/provider selection never changes a thread's authority. Codex and OpenCode receive the same Owner Direct discovery, audit, and write-preparation tools; the final write confirmation remains UI-owned. Codex safe mirror reads and validators run automatically. OpenCode native shell and edits are denied and its reviewed MCP requests cross the ToolBroker. Real repository file changes pause on client approval. P7 and P10 remain available as legacy governed boundaries.

Before either agent harness starts, the conversation engine handles two bounded cases locally: a standalone greeting and a positively resolved, unambiguous documented-IP lookup that does not request current or live verification. The latter includes the canonical source and says that it was not live-verified. A zero-match or multiple-match resolution is a fast-path miss and falls through to the selected AI engine for investigation; it is never returned as a local final answer. Words such as `live`, `current`, `verify`, or `check now` also bypass this latency fast path and continue through the selected Codex/OpenCode engine and governed live-read controls. Turn events identify `LOCAL_DETERMINISTIC_FAST_PATH` and `provider_invoked: false` so this optimization is auditable.

- `GET /api/v2/tools`
- `POST /api/v2/tool-calls`
- `POST /api/v2/tool-calls/{tool_call_id}/invoke`
- `POST /api/v2/live-reads/{live_read_id}/approve`
- `POST /api/v2/live-reads/{live_read_id}/execute`
- `POST /api/v2/workspace/plans/{plan_id}/approve`
- `POST /api/v2/workspace/rollbacks/{rollback_id}/approve`

Workspace application verifies the resulting state. A reverse patch is offered only while the post-apply digest still matches and needs a new exact owner approval.

An exact IP lookup in `LIVE_READ` mode deterministically proposes `mne.prepare_live_read` when one canonical entity maps to an active P7 binding. `OWNER_FULL_CONTROL` instead consumes the same short-lived session-bound P7 read authorization internally, without a second read click. The server revalidates the canonical target, registered check, pinned identity, configured credential target, owner session, plan digest, expiry, and replay state. A successful normalized transport result creates one schema-valid trust-5 evidence record; any blocker returns no evidence and receives no automatic retry. P7 remains globally disabled at rest. P10 keeps its separate session-bound risk, complete approval, post-check, and declared-failure rollback boundary.
