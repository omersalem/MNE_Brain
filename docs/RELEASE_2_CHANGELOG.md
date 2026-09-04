# MNE_Brain Release 2 — Architectural Delta & Evolution Matrix

> **Baseline Project:** `MNE_Brain_v1` (Frozen Baseline)  
> **Target Project:** `MNE_Brain_v2` (Independent MNE_Brain Workspace)  
> **Core Philosophy:** A Senior Infrastructure Engineer Implemented in Software  
> **Author:** Chief Software Architect & Brain Architect  

## 2026-08-31 - OpenCode complete secondary AI engine

- Removed the previous CLI-specific and direct-provider secondary implementations, profiles, environment names, adapters, installation guidance, and active tests.
- Added a supervised authenticated `opencode serve` runtime on random loopback, health checks, graceful shutdown, bounded restart, cancellation, timeout, and safe error mapping.
- Added dynamic providers, authentication methods, model capabilities/limits/status/cost labels, explicit model pinning, API-key and OAuth/device flows, environment references, and validated custom OpenAI-compatible endpoints.
- Added a credential-free controlled MCP relay to the existing ToolBroker. Native OpenCode shell, editing, broad reads, web access, and ungoverned tools are denied; P7 and P10 boundaries remain unchanged.
- Added legacy conversation migration: active future turns require an explicit OpenCode model while historical per-turn attribution is preserved. No live infrastructure write was performed.

## 2026-08-30 - Codex App Server GUI harness

- Fixed turns that appeared to complete without a visible result: the bridge now publishes the authoritative completed `agentMessage` as `answer.final`, rejects genuinely empty completions with a retryable diagnostic, and collapses activity details after completion so the answer area is visible.
- Added an always-visible, collapsible live background-activity timeline that presents redacted progress, plans, sandbox commands and output, governed tool/evidence/validation lifecycle, approval waits, answer composition, and terminal status without exposing credentials or private model reasoning.
- Removed repetitive prompts for exact read-only skill, memory, attachment, and plugin-cache inspection by extending the server-side safe-read classifier to narrowly allowlisted roots. Real writes now emphasize one approval for the complete displayed batch; unseen future mutations remain separately gated.
- Replaced the GUI's primary custom provider turn loop with a supervised local Codex App Server JSONL/JSON-RPC bridge authenticated by the existing ChatGPT session.
- Added dynamic repository/worktree discovery, credential-free per-thread mirrors, child-environment allowlisting, `service_tier="fast"` child override, exact port-conflict reporting, and readiness UI/API.
- Streamed Codex progress, plans, command output, diffs, governed tools, approvals, and terminal state through the existing redacted SSE contract.
- Kept P7 as the only live-read path and P10 as the only infrastructure-write path. Direct infrastructure shell commands are declined; P10 dynamic tools prepare only.
- Live-validated automatic repository inspection, trust-level-5 P7 evidence, file deny/approve/validation, and separately approved rollback. Global P10 execution remains disabled.

## 2026-08-24 - Fast conversation and documented-read path

- Removed the ordinary external-data authorization popup. The server now automatically prepares and consumes the same exact single-use digest for sanitized conversation and exact documented workspace context; supplied live evidence remains explicitly gated.
- Added deterministic natural-language entity matching for unique location-plus-product queries and injects only a compact, source-labeled, non-live baseline record.
- Kept one SSE response open through each terminal turn event, eliminating the browser's repeated reconnect delay while preserving last-event-ID resumption.
- Constrained the desktop workspace to the available viewport so the message history scrolls while the follow-up composer and governed-operations drawer remain visible; mobile layouts retain document flow.
- Added the exact `fmc` alias to the canonical Cisco FMC entity so short questions resolve to the documented `172.23.70.77` management address with its existing unverified/non-live truth label.
- Corrected the Tulkarm branch baseline to `10.165.18.0/24`, added the exact `sw-cisco-tulkarm-01` access-switch entity at documented management IP `10.165.18.3`, and retained an explicit unverified/non-live truth label.
- Added a fail-closed deterministic IP lookup path: exact documented targets are answered directly from the canonical record without asking an external model to guess; unresolved or ambiguous targets return no address.
- Live follow-up completed a public prompt in 1.18 seconds and the exact documented Hebron FortiGate lookup in 1.41 seconds. P7 reads and P10 writes remained disabled.

## 2026-08-24 - Provider reliability, workspace safety, and GUI completion

- Hardened the provider gateway to return bounded stable errors without provider bodies, secrets, or stack traces.
- Added cancellation checkpoints, one active turn per thread, safe in-memory diagnostics, retry/copy recovery controls, and suppression of empty assistant messages.
- Added password-authenticated `OWNER_AUTONOMOUS` as the only selectable GUI mode; legacy permission modes remain import-compatible and provider selection remains independent of authority.
- Hardened workspace boundaries against traversal, secret paths, symlink escape, wildcard/command syntax, and unverified mutations. Workspace rollback now requires a separately approved, five-minute, state-bound reverse patch and post-apply verification.
- Added safe in-memory conversation export/import and completed the responsive, accessible, light/dark presentation console with exact diff and tool lifecycle rendering.
- Validated the external-provider stream contract with a harmless public prompt; no Ministry data or infrastructure tools were used. P7 reads and P10 writes remained disabled.
- Passed 196 full tests, 50 focused P11 tests, 20 P11 pilot scenarios, 22 master gates, 57 architecture checks, 11 benchmarks, 152 Python syntax checks, ten GUI syntax checks, and a 386-file plaintext-secret audit.

External Ministry data, P7 reads, and real P10 writes remain disabled pending their separate exact authorizations.

---

## 2026-08-20 — P11 control plane

- Added ADR-018 and ten strict conversation/provider/tool schemas.
- Contained the API with loopback binding, same-origin owner sessions, strict cookies, CSRF, one-time nonces, inactivity expiry, bounded concurrency, SSE, and cancellation.
- Quarantined synthetic ChatGPT OAuth and removed plaintext provider JSON storage from the server path.
- Added six reviewed provider profiles, normalized provider events, OpenAI `store: false`, deterministic SSRF policy, exact external-data authorization, and a centralized tool broker.
- Rebuilt the GUI as nine presentation-only modules and added P11 tests, pilot, CI, and master gate 22.

External calls, live reads, and real P10 writes remain disabled.

---

## 🏛️ Comprehensive Architectural Delta Matrix

The table below outlines the evolution from `MNE_Brain_v1` to `MNE_Brain_v2`.

| Component | Release 1 Baseline (`MNE_Brain_v1`) | Release 2 Architecture (`MNE_Brain_v2`) | Architectural Delta | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Project Structure** | Single repository directory path. | Completely independent project roots (`MNE_Brain_v1` & `MNE_Brain_v2`). | **Separate Root Paths** | Eliminates path interference, isolated git lifecycles. |
| **Governance & Contracts** | Unenforced specs & manual checks. | **Milestone 1: Architecture Contracts** (`00_meta/schemas/`, ADRs). | **Contracts-First Milestone** | Governs rules & schemas before implementation begins. |
| **Retrieval Philosophy** | ~~Traditional RAG / Text Search~~ | **Knowledge Discovery Engine** & **Evidence-Driven Retrieval** | **RAG Replacement** | Capped at <1,500 tokens with 5-tier trust attribution. |
| **Knowledge Evolution** | Manual note updates. | **Knowledge Lifecycle Engine (`core/lifecycle/`)** | **Knowledge Lifecycle** | Drift detection, review queue, promotion tracking; **zero auto-overwrites**. |
| **Execution Architecture** | Direct tool execution in scripts. | **Execution Engine (`core/execution/`) vs Tool Drivers (`core/tools/drivers/`)** | **Execution / Driver Split** | Execution handles retry, audit, rollback; drivers are simple protocol connectors. |
| **Policy Engine** | Static policy table in YAML. | **Dedicated Policy Engine (`core/policy/`)** | **Policy Engine Layer** | Evaluates verification necessity, read-only policy & risk. |
| **GUI Architecture** | CLI terminal commands. | **Presentation Dashboard (`gui/`)** | **Presentation-Only GUI** | **ZERO Business Logic in GUI**. Presentation ONLY. |
| **Investigation** | Static linear markdown steps. | **Stateful Investigation Graph** | **Information Gain Engine** | Enables Stop Early principle after root cause certainty. |
| **LLM Provider Layer** | Hardcoded model calls. | **Codex plus OpenCode engines** | **Dynamic Provider Abstraction** | Codex primary; OpenCode discovers connected vendors and models at runtime. |
| **Validation Gate** | 12-step validation script. | **15-Step Quality Gate & 11 Infrastructure Benchmarks** | **MNE_Brain Verification** | Tests MNE_Brain infrastructure performance directly. |

---

## 🔍 Summary of Preserved Assets

1. **3-Layer Decoupled Architecture (`knowledge/`, `operations/`, `intelligence/`).**
2. **Declarative Device Profiles (`profiles/*.yaml`).**
3. **5-Tier Trust Level Standard ($\star\star\star\star\star$ scale).**
4. **Controlled Autonomous Remediation Framework (Level 0 to Level 4).**
5. **Zero-Trust Credential Isolation Policy (`.env` local storage).**

---

## 2026-08-20 — P10 owner-controlled write execution

- Added ADR-017, nine strict schemas, the sole-owner P10 policy, seven catalog families, 56 templates, and 176 action variants.
- Added exact five-minute prepare/approve/execute/rollback workflows with cataloged, critical, and irreversible phrases.
- Added eight disabled-by-default platform adapter families, local-only CSRF/replay-protected API endpoints, and a presentation-only GUI view.
- Changed Level 4 from a universal prohibition to `CRITICAL_EXCEPTION_ONLY`; the legacy path remains non-executing.
- Added 42 focused tests and a 23-scenario multi-platform offline pilot with zero live connections.
