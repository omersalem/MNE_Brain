# P11 Codex App Server Integration

## Outcome

The loopback GUI is now a presentation client for the same local Codex harness used by Codex clients. `core/codex/app_server.py` supervises `codex app-server` over bidirectional JSONL/JSON-RPC, initializes the protocol, creates or resumes Codex threads, starts and interrupts turns, handles server requests, and maps App Server events into the existing SSE envelope.

The integration authenticates with the Windows user's existing `codex login` ChatGPT session. It does not require or inherit `OPENAI_API_KEY`. A process-local `service_tier="fast"` override avoids the workstation's incompatible global `service_tier=default` value without modifying global Codex configuration.

## Start

```powershell
cd D:\projects\MNE_Brain_v2
codex -c 'service_tier="fast"' login status
python scripts/configure_owner_login.py   # only when owner login is not configured
python core/api/server.py
```

Open `http://127.0.0.1:8080`. To use another loopback port:

```powershell
$env:MNE_BRAIN_PORT='8088'
python core/api/server.py
```

The server fails with a clear conflict message if the selected port is already in use. It never silently moves to another port.

## Readiness

`GET /api/v2/codex/readiness` and the GUI Settings panel report:

- Codex binary discovery;
- ChatGPT authentication;
- App Server help and initialization;
- discovered repository/worktree root;
- `workspace-write` sandbox with network disabled;
- `untrusted` client approval policy;
- process-local `fast` service tier override;
- restart count and last safe failure;
- P7 owner-scoped availability and binding counts;
- P10 global execution state and non-secret platform blockers.

## Security and authority

Each GUI thread receives a disposable mirror of the active Git root. The mirror excludes `.git`, every non-example `.env`, known credential stores, audit state, private-key formats, symlinks, dependency/cache trees, and files over 10 MB. The child environment is rebuilt from a small OS allowlist and does not inherit MNE variables, API keys, passwords, tokens, or credentials from the API process.

Codex receives five Responses-compatible dynamic tools:

- `mne_build_evidence` -> `mne.build_evidence`;
- `mne_plan_investigation` -> `mne.plan_investigation`;
- `mne_prepare_live_read` -> `mne.prepare_live_read`;
- `p10_prepare` -> `p10.prepare`;
- `p10_prepare_critical` -> `p10.prepare_critical`.

Safe local reads and validators run automatically in the disposable mirror. Exact read-only paths under installed Codex/agent skills, memories, user attachments, and installed plugin caches are also automatically accepted after command-shape, path-root, protected-name, and mutation checks; they remain visible in the activity trace but never create an approval card. Direct infrastructure/network commands are declined. Other untrusted commands require a one-time approval and still run only in the mirror. A Codex file change is converted to one exact real-repository unified diff batch; the server displays all paths, commands/diff, risks, impact, prechecks, post-checks, rollback procedure, digest, and exact phrase before one approved application. Rollback requires its own exact approval. P10 execution is not exposed as a dynamic tool, so the agent can prepare but cannot approve or execute an infrastructure write.

The approval UX is intentionally consolidated at the mutation boundary: automatic reads need no click, while one approval covers every exact path or infrastructure action shown in the displayed batch. That approval never includes unseen future changes; a later materially different batch receives its own complete preview.

## Stream mapping

The GUI receives agent commentary and final text, plan updates, command start/output/completion, file changes and diffs, dynamic tool lifecycle, approval requests, and terminal turn status. EventSource reconnect uses `Last-Event-ID`; refreshing the GUI reattaches to any queued or running turn. If App Server exits, the active turn fails safely and the next turn starts a new process and resumes its mapped Codex thread when available.

The conversation area includes a live background-activity panel. It coalesces streaming progress and presents the redacted operational trace as it happens: plans, local sandbox commands and output, governed tool lifecycle, accepted evidence, validation, approval waits, answer composition, and terminal status. It deliberately does not expose credentials, environment secrets, or private model reasoning. Exact write previews and approval controls remain in the detailed governed-operations drawer.

## Acceptance evidence (2026-08-30 UTC)

- Read-only repository investigation completed through a safe automatic PowerShell read and returned the exact README heading.
- The Codex mirror was verified to contain neither `.env` nor `.git`.
- A live P7 `system_status` read for the pinned FortiGate target `172.23.70.4` returned fresh trust-level-5 evidence; no write was attempted.
- File denial left the real repository unchanged.
- Exact approval created only `codex_harness_acceptance.tmp`; `git diff --check` passed.
- A separately approved rollback removed the acceptance file and verified the original state.
- Direct SSH command preparation is automatically declined and cannot become an approval.

These checks validate the harness and governed paths at that time. They do not enable global P10 execution or establish general production readiness.
