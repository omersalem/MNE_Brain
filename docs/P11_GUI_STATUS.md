# P11 GUI Status

The GUI is a polished presentation-only infrastructure console with:

- responsive conversation navigation and search;
- one continuous streamed user/assistant connection per turn, with cancellation and real reconnect status;
- exactly two AI engines, Codex primary and OpenCode secondary, with server-enforced `OWNER_DIRECT` mode;
- live OpenCode provider/auth/model discovery, capability and limit metadata, free/paid/unknown cost labels, API-key and OAuth/device flows, environment references, validated custom endpoints, and safe connection indicators;
- evidence sources, unknowns, and live-gate status;
- automatic-read progress cards, Owner Direct evidence IDs, connection/authentication state, identity conflicts, exact write risk warnings, a final-confirmation control, complete canonical coverage and readiness table, exact workspace diff review/apply/verification, and full legacy P10 previews;
- clear provider failures with Retry and Copy diagnostic details actions;
- no empty assistant bubble when a request fails before text arrives;
- offline state, empty state, loading state, keyboard send, focus styling, reduced-motion support, and desktop/tablet/mobile layouts;
- light and dark themes;
- safe in-memory conversation export/import.

The eleven modules are `api.js`, `auth.js`, `threads.js`, `composer.js`, `streaming.js`, `activity.js`, `evidence.js`, `tool_calls.js`, `approvals.js`, `providers.js`, and `p10.js`. `auth.js` presents password login/logout while the server owns verification, lockout, cookies, CSRF, and nonce checks. Ordinary external messages and registered reads run without authorization popups. The modules create DOM nodes and assign `textContent`; they display server-built risks, commands, rollback, and approval phrases but never calculate them or decide tool eligibility.

## Deep live investigations

- The server now creates a bounded plan of no more than three immutable P7 checks when a question has a governed live path.
- An explicit unknown IP fails entity resolution instead of selecting an unrelated document from generic words such as `server`.
- FortiGate policy questions accept an IP, hostname, service name, or address-object alias; they use address-object resolution followed by policy inspection on the exact pinned firewall binding.
- When a provider requests multiple live reads in one response, every normalized result is retained for final reasoning rather than only the last result.
- The GUI shows `Deep live plan` status and accumulates each attributable live evidence source.
- Raw device output and credentials are never returned to the conversation. The transport produces bounded normalized facts for AI reasoning.
- Reads may run automatically only inside an authenticated owner session. Owner Direct writes display exact commands, risk, identity state, postchecks, and rollback/no-safe-rollback information, then require one final confirmation. Legacy P10 remains available for existing cataloged plans.
