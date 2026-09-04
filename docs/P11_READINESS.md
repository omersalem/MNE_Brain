# P11 Readiness

## Implemented and validated

- loopback owner-session containment, CSRF, nonce, origin, inactivity, and concurrency controls;
- in-memory thread, turn, message, event, sanitized diagnostic, and portable export/import lifecycle;
- continuous reconnect-safe SSE, cancellation, bounded timeout, one-active-turn protection, and no duplicate empty assistant result;
- Codex App Server primary and supervised OpenCode secondary engines, with the legacy deterministic provider retained for offline control-plane tests but not exposed as a GUI AI engine;
- provider-free local fast answers for bounded greetings and unambiguous documented-IP lookups on both GUI engines; explicit `live`, `current`, or verification wording bypasses the fast path and retains governed investigation;
- supervised ChatGPT-authenticated Codex JSONL/JSON-RPC, thread resume, turn cancellation, process recovery, dynamic P7/P10 preparation tools, and streamed agent/plan/command/diff/approval events;
- OpenCode loopback Basic Auth, health supervision, bounded restart, provider authentication, dynamic provider/model discovery, explicit model pinning, SSE parsing and reconnection, cancellation, timeout, and safe errors;
- automatic exact authorization and redaction for conversation, documented baseline, and owner-requested read-only evidence without a popup;
- `OWNER_FULL_CONTROL` enforcement for new GUI threads, with legacy permission modes retained only for imported conversations;
- credential-free per-thread repository mirrors, allowlisted child environment, safe automatic reads/validators, exact real-repository diff approval, post-apply verification, and separately approved state-bound rollback;
- deterministic exact-entity P7 proposals, five-minute owner-session-bound phrase approval, single-use execution, and schema-valid attributable evidence only after a successful injected transport result;
- bounded deep-live planning, strict explicit-IP resolution, two-stage FortiGate policy-by-IP discovery, and multi-read evidence continuation before the final answer;
- responsive accessible presentation-only GUI.

## Disabled or separately gated

- P7 live reads remain globally disabled at rest; each real read requires one exact registered target/check/binding, a configured credential target, and a trusted identity pin. In an authenticated `OWNER_FULL_CONTROL` session the server creates and consumes the exact short-lived authorization internally; legacy `LIVE_READ` mode retains displayed approval;
- P10 infrastructure writes remain disabled at rest and require the complete P10 pre-check, plan, session-bound exact phrase, execution, independent post-check, and the displayed rollback only on its declared failure condition;
- conversations and diagnostics are not persistently stored;
- local Ollama has not been live-validated;
- production readiness and current Ministry health are not established by GUI/provider validation.

Codex App Server uses the existing `codex login` ChatGPT session and a child-only `service_tier="fast"` override. It receives no API key or device credential. OpenCode receives provider credentials only through its own authenticated API or environment references; MNE_Brain never returns those secrets to the browser. Readiness of either local engine does not establish provider availability, Ministry health, or P10 authority.
