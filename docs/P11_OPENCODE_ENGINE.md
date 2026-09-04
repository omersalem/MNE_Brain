# P11 OpenCode Secondary AI Engine

## Purpose

OpenCode is the complete secondary AI engine beside the primary Codex App Server. The application supervises a local `opencode serve` process, discovers providers and models dynamically, supports OpenCode-reported provider authentication methods, runs multi-turn conversations with explicit model pinning, and exposes only governed MNE_Brain tools.

## Install and start

Install OpenCode as the same Windows user that starts MNE_Brain:

```powershell
npm install -g opencode-ai
opencode --version
python core/api/server.py
```

At application startup the supervisor resolves the executable without invoking a command shell, requires OpenCode 1.0.0 or newer, chooses an available loopback port, generates a high-entropy password in memory, and starts:

```text
opencode serve --hostname 127.0.0.1 --port <random-port> --pure --log-level ERROR
```

`OPENCODE_SERVER_PASSWORD` is supplied only to the child process. The password and generated authorization header are never written to repository files, browser payloads, events, diagnostics, or logs. Startup succeeds only after authenticated `/global/health` reports healthy. The process is stopped with instance disposal and bounded termination. Unexpected exit allows at most three bounded exponential restart attempts; active turns fail safely and are never silently retried on another model.

## Provider authentication and catalog

Open Settings in the GUI and refresh OpenCode. Provider cards and the model selector are built from live `/provider` and `/provider/auth` responses rather than a hard-coded vendor list.

- API key: select a provider, enter the key, and submit it once. MNE_Brain removes the value from the form and request object immediately after forwarding it to authenticated loopback OpenCode. It does not persist or return the value.
- OAuth or device code: choose a method reported by OpenCode, complete any provider-specific prompts, and start the flow. The GUI opens the exact HTTPS authorization URL returned by OpenCode. If OpenCode requests a code, enter it in the completion form.
- Environment reference: configure a reviewed environment variable outside tracked files and list its name in `OPENCODE_PROVIDER_ENV_REFS` (comma-separated), or select it in custom-provider metadata. Only explicitly named AI-provider variables are copied into the child environment. The value is resolved by OpenCode at runtime and is not returned by MNE_Brain; MNE device credential variables are never inherited wholesale.
- Custom OpenAI-compatible endpoint: provide a provider ID, HTTPS base URL, protocol, model metadata, optional environment reference, and non-secret headers. Private, reserved, link-local, metadata, credential-bearing, query, fragment, file, and unsafe endpoints are rejected. Plain HTTP is permitted only for an explicitly approved loopback local-model endpoint. Custom metadata is non-secret and stored in `config/opencode_custom_providers.json`.

Anthropic account OAuth may violate provider terms outside approved clients. The UI reports a warning when OpenCode advertises that method; use an approved API key or provider-authorized method unless organizational policy explicitly permits it.

## Conversations and model behavior

Create a new conversation, choose OpenCode, and select one exact connected provider/model. The thread stores both provider/model attribution and engine identity. The selection is pinned after the first turn. If a provider or model disappears, the thread pauses and asks the owner to select an available model; it does not choose one silently.

Only final answer text is stored and rendered. OpenCode reasoning content is ignored. Tool progress is normalized into safe activity events. Owner cancellation calls the OpenCode session abort endpoint. Timeouts, malformed streams, provider errors, process exits, and incomplete responses produce bounded errors without provider bodies or secrets.

The readiness/diagnostic state contract includes `READY`, `NOT_INSTALLED`, `VERSION_UNSUPPORTED`, `STARTING`, `AUTH_REQUIRED`, `NO_CONNECTED_PROVIDER`, `NO_MODELS`, `MODEL_REMOVED`, `RATE_LIMITED`, `SERVER_UNAVAILABLE`, and `CONNECTION_FAILED`. Turn cancellation, timeout, and empty-answer failures use separate safe codes. A provider or model error never changes P7/P10 authority.

Legacy V1 conversation imports keep historical per-turn attribution unchanged. Their active future engine is migrated to OpenCode with `select-model`, requiring an explicit available model before the next turn. V2 exports preserve engine, provider, and model on every turn.

## Governed tools and write safety

The OpenCode child receives no MNE infrastructure credentials. Native shell, file editing, task delegation, broad filesystem tools, web fetch/search, skills, questions, and external-directory access are denied. The only enabled MCP tools forward to the existing server-side ToolBroker:

- bounded workspace list, search, read, status, and diff;
- evidence-pack construction and investigation planning;
- exact governed P7 live-read preparation/execution through the established owner-scoped policy;
- cataloged and critical P10 plan preparation.

OpenCode cannot approve or execute P10. The GUI displays the server-built current-state evidence, exact scope and target, dependencies, ordered commands or API operations, expected impact, prechecks, postchecks, rollback strategy, non-rollbackable warning, identity/state hashes, expiry, and risk. One exact owner approval covers only that immutable bundle. Execution, if separately enabled, still verifies target identity, command hash, state digest, policy, credential reference, and freshness. Rollback is a new prepared plan with a new approval.

## Direct OpenCode terminal

Direct terminal use is intentionally separate from the governed GUI integration:

```powershell
Set-Location D:\projects\MNE_Brain_v2
opencode
```

The direct terminal uses the user's normal OpenCode configuration and permissions. It is not protected by the MNE_Brain ToolBroker or GUI P10 approval flow, so do not use it for live Ministry changes unless a separate approved operating procedure explicitly authorizes that work.

## Troubleshooting

- `NOT_INSTALLED`: install `opencode-ai`, confirm `opencode --version`, and restart the MNE_Brain server.
- `START_FAILED` or health timeout: confirm no endpoint security product blocks the OpenCode executable or loopback child process. The application uses a random port and does not expose it externally.
- Provider is disconnected: use one of the authentication methods shown on its live provider card, then refresh.
- Model disappeared: refresh the catalog and explicitly choose another connected model for the affected conversation.
- OAuth popup blocked: allow the popup or copy/open the exact authorization URL shown by the browser flow; never substitute a different URL.
- Custom endpoint rejected: use HTTPS and a public, credential-free base URL, or explicitly approve only a true loopback endpoint for a local model.
- Turn failed after a child exit: review the bounded readiness error and retry after the supervisor is healthy. No turn is replayed automatically.

## API summary

The owner-authenticated local API exposes OpenCode readiness/catalog refresh, API-key connection, OAuth start/callback, disconnect, non-secret configuration test, custom provider save/remove, and runtime restart routes under `/api/v2/opencode/`. Conversation creation and engine pinning use the existing P11 thread routes. Every mutation retains the same owner session, same-origin, CSRF, nonce, and body limits as the rest of P11.

Official references reviewed for this integration: [server API](https://opencode.ai/docs/server/), [providers](https://opencode.ai/docs/providers/), [configuration](https://dev.opencode.ai/docs/config), and [permissions](https://opencode.ai/docs/permissions/).
