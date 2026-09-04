# P11 AI Engine Gateway

The owner GUI exposes exactly two AI engines: Codex as primary and OpenCode as secondary. The browser never calls either engine directly. The server owns conversation attribution, policy, evidence, ToolBroker routing, redaction, cancellation, and the P10 approval boundary.

OpenCode is queried at runtime for providers, connected providers, authentication methods, models, capabilities, context/output limits, model status, and cost metadata. A model is labelled `FREE` only when every reported numeric input/output/cache cost is zero, `PAID` when any reported cost is positive, and `UNKNOWN` when cost data is incomplete. Labels are informational and never promise eligibility, quota, or availability.

Each OpenCode turn creates or resumes a server-side OpenCode session and sends the exact selected `{providerID, modelID}`. There is no silent provider or model fallback. Text deltas, tool activity, usage, idle completion, cancellation, timeout, and failures are normalized into the existing redacted conversation event stream. Private reasoning is not stored or rendered.

OpenCode native shell, native file edits, broad reads, web access, and unreviewed tools are denied in both its inline configuration and per-session permissions. Only the controlled `mne_brain` MCP relay is enabled. The relay has one active-turn capability, no repository or device credentials, and forwards reviewed requests to the parent ToolBroker on loopback. P7 remains the only live-read path and P10 remains the only infrastructure-write path.

See [P11 OpenCode Engine](P11_OPENCODE_ENGINE.md) and the official [OpenCode server API](https://opencode.ai/docs/server/), [provider guide](https://opencode.ai/docs/providers/), [configuration guide](https://dev.opencode.ai/docs/config), and [permissions guide](https://opencode.ai/docs/permissions/).
