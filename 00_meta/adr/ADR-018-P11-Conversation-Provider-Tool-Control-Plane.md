# ADR-018: P11 Conversation, Provider, and Tool Control Plane

- Status: Accepted
- Date: 2026-08-20
- Depends on: ADR-007, ADR-012, ADR-014, ADR-017

## Decision

P11 adds a local, owner-controlled conversation control plane without weakening any earlier safety boundary.

- A **thread** is an in-memory conversation container. A **turn** is one bounded user request and its processing lifecycle. A **message** is a user-visible content item within a thread.
- A **provider** is a declared model endpoint profile. Selecting or switching a provider changes only model execution; it never changes tool permissions.
- A **tool call** is a schema-valid proposal. Registered non-mutating reads may execute automatically under an authenticated owner session; model output never executes a write directly. A write **approval** is a short-lived, owner-session-bound authorization over an exact immutable digest. An **event** is a redacted user-visible lifecycle envelope.
- The GUI is presentation-only. It renders server state and submits owner input; it does not compute risk, permissions, hashes, approval phrases, evidence eligibility, or commands.
- AI may reason and emit structured proposals. Deterministic Python alone validates schemas, evidence, authorization, permissions, paths, commands, provider boundaries, and execution state.
- `knowledge/`, `operations/`, and `intelligence/` remain separate. Chat content is not promoted to canonical knowledge automatically.
- Threads, turns, messages, events, approvals, and external-data authorizations are in memory by default and have no persistence contract.
- External model selection does not grant tools. The authenticated local owner establishes standing authorization for sanitized conversation and registered read-only evidence so ordinary questions do not pause. Provider context is still redacted and exact; credentials and raw device output remain prohibited.
- Workspace writes use the P11 tool broker and exact approved unified diffs. Ministry infrastructure writes are impossible through the workspace broker and can enter only through P10.
- P7 remains the only live-read execution boundary. P10 remains the only infrastructure-write execution boundary. Real P10 execution remains disabled until separately authorized.
- User-visible streams never expose hidden reasoning, credentials, raw device output, unredacted configuration, rollback secrets, or operational logs.
- Codex App Server is the primary local agent harness. It uses the existing ChatGPT session over JSONL/JSON-RPC, a dynamically discovered checkout/worktree, a credential-free disposable mirror, network-disabled workspace sandboxing, and client-mediated approvals.
- Codex receives dynamic preparation/read tools only. It cannot approve or execute P10, and direct infrastructure commands are declined rather than treated as workspace operations.
- OpenCode is the complete secondary AI engine. It runs as a supervised random-port loopback server with an in-memory Basic Auth password, dynamic provider/auth/model discovery, explicit exact model pinning, normalized SSE, bounded restart, and no silent fallback.
- OpenCode native shell, edit, broad-read, web, and ungoverned tools are denied. Its one-active-turn MCP capability forwards only reviewed requests to the existing ToolBroker and receives no repository or device credential.

## Security invariants

1. The primary server binds to loopback, requires a configured password verifier, allows one owner session, and accepts API mutations only from that same-origin loopback session.
2. Owner mutations require an HttpOnly `SameSite=Strict` cookie, CSRF token, inactivity-valid session, and a one-time nonce.
3. Provider credentials remain server-side. Tracked files contain credential reference names only.
4. Custom provider URLs are subject to deterministic SSRF policy. External endpoints require reviewed HTTPS origins; local adapters require loopback.
5. Provider failures never trigger automatic retries after a possible tool side effect.
6. `LIVE_VERIFIED` requires fresh attributable evidence. Conversation summaries cannot change evidence status.

## Consequences

The API becomes concurrently bounded and supports SSE reconnection and cancellation. Provider-specific wire formats are translated to canonical provider events. Tool execution is centralized and fail-closed. The P11 GUI may be replaced independently because it owns no business decisions.

## Acceptance

This ADR is accepted only while it agrees with `AGENTS.md`, `docs/P10_SAFETY_CONTRACT.md`, the strict P11 schemas, and the offline master validation gate. Where operational skill guidance conflicts with the implementation plan supplied by the owner, the supplied plan controls while all explicit P10 safety restrictions remain intact.
