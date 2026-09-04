# MNE_Brain Release 2 (v2)

> **Status:** The GUI uses the local ChatGPT-authenticated Codex App Server harness as its primary AI engine and a supervised loopback OpenCode server as its complete secondary AI engine. OpenCode providers, authentication methods, models, limits, capabilities, status, and free/paid/unknown cost labels are discovered dynamically. Safe reads and governed P7/P10 preparation are available through the same server-side control plane. P10 is still the only infrastructure-write path and remains disabled at rest. Production readiness is not claimed.

Release 2 is the independent implementation line for an evidence-driven Ministry infrastructure investigation platform. Release 1 remains a separate reference baseline and is not modified by this project.

The intended pipeline is:

```
Question or alert -> entity resolution -> focused evidence -> AI investigation plan
-> bounded read-only verification -> evidence-based answer -> controlled remediation
```

The GUI is presentation-only. Deterministic code enforces scope, policy, evidence handling, and safety boundaries; AI reasoning develops hypotheses and investigation plans.

See [the development baseline](docs/DEVELOPMENT_BASELINE.md) and [current Release 2 status](docs/RELEASE_2_STATUS.md) before running the project.

P7 implements SSH, REST, PowerShell/WinRM, VMware, SNMP-readiness, and bounded TCP preflight behind exact-target and identity gates. It enables no remediation, notification, ticket, page, assignment, or persistent audit/evidence storage. See [P7 live validation](docs/P7_LIVE_VALIDATION_REPORT.md) and [P7 readiness](docs/P7_READINESS.md).

P8 adds eight exact-scope troubleshooting scenarios, safe reconciliation for all 32 operational bindings, fresh trust-5 evidence intake, a compact root-cause reasoning handoff, and a planning-only GUI/API. The planner never connects; the local live pilot requires explicit owner `proceed` and retains no raw output. See [P8 plan](docs/P8_PLAN.md), [P8 readiness](docs/P8_READINESS.md), and [P8 live validation](docs/P8_LIVE_VALIDATION_REPORT.md).

P9 adds 30 platform-specific deep checks, ephemeral output normalization, adaptive information-gain ordering, evidence-referenced AI assessments, and a 95% stop-early gate. Python does not diagnose. Veeam remains unreachable from this workstation; vCenter inventory authorization, FMC API access, DC2 WinRM, the actual SAN controller, and Fujitsu SW2 identity remain explicit gaps. See [P9 plan](docs/P9_PLAN.md), [P9 readiness](docs/P9_READINESS.md), and [P9 live validation](docs/P9_LIVE_VALIDATION_REPORT.md).

P10 adds seven reviewed operation families, 56 schema-governed templates, 176 action variants, five-minute exact owner approval bound to the complete immutable plan and loopback owner session, global single execution, zero write retries, independent post-checks, and declared-failure automatic rollback from the same displayed approval. P10 remains disabled at rest. Exact live rendering exists for 87 actions and 89 underspecified actions fail closed. See [Owner Full Control](docs/OWNER_FULL_CONTROL.md), [P10 plan](docs/P10_PLAN.md), [P10 safety contract](docs/P10_SAFETY_CONTRACT.md), [P10 readiness](docs/P10_READINESS.md), [live readiness report](docs/P10_LIVE_EXECUTION_READINESS_REPORT.md), and [P10 offline validation](docs/P10_OFFLINE_VALIDATION_REPORT.md).

P11 adds password-authenticated loopback `OWNER_FULL_CONTROL`, in-memory conversations, reconnect-safe SSE/cancellation, seven reviewed profiles, and an eleven-module presentation-only GUI. Codex App Server is primary and uses the existing `codex login` ChatGPT session—no API key. OpenCode is secondary and supervises its own dynamic provider/model connections behind in-memory Basic Auth. Both engines have equal governed investigation and P10 preparation capability. Safe reads and validation run automatically; real repository and infrastructure writes remain server-controlled. See [Codex App Server integration](docs/P11_CODEX_APP_SERVER.md), [OpenCode integration](docs/P11_OPENCODE_ENGINE.md), [Owner Full Control](docs/OWNER_FULL_CONTROL.md), [P11 safety contract](docs/P11_SAFETY_CONTRACT.md), [P11 API](docs/P11_API.md), and [P11 readiness](docs/P11_READINESS.md).

The reusable authenticated baseline is `python scripts/run_p7_authenticated_baseline.py --owner-proceed`. It executes only the 32 active schema-governed bindings, skips the owner-excluded Ramallah Gold switch, summarizes results without raw output, and leaves live policy disabled at rest.

## Local development setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Offline quality gate

```powershell
python scripts/validate_schemas.py
python scripts/validate_p0_containment.py
python scripts/validate_brain.py
python scripts/run_owner_direct_offline_pilot.py
python scripts/run_benchmarks.py
python scripts/run_p6_offline_pilot.py
python scripts/run_p8_offline_pilot.py
python scripts/run_p9_offline_pilot.py
python scripts/run_p10_offline_pilot.py
python scripts/run_p11_offline_pilot.py
python scripts/validate_gui_javascript.py
python -B -m pytest -q -p no:cacheprovider tests/test_p10_phase.py
python -B -m pytest -q -p no:cacheprovider tests/test_p11_phase.py
python -B -m pytest -q -p no:cacheprovider tests/test_p11_codex_app_server.py
python -B -m pytest -q -p no:cacheprovider tests/test_p11_opencode_runtime.py
$env:PYTHONDONTWRITEBYTECODE='1'
python -B -m pytest -q -p no:cacheprovider -m "offline or integration"
```

The complete current test collection is classified and safe to run offline. It uses disposable fixtures for recovery, failure, and scalability scenarios. Passing it does not demonstrate live service health, credential safety, or production readiness.

## P2 boundary

P2 adds fail-closed read-only adapter contracts, attributable live-evidence normalization, offline operational pilots, and operator runbooks. Simplified P0 Git containment is complete: local `.env` files may contain secrets and remain ignored. The first exact-target FortiGate pilot succeeded through the pinned adapter, and repository live policy was disabled immediately afterward. See [the P0 containment policy](docs/P0_SIMPLE_CONTAINMENT.md), [the P2 pilot result](docs/P2_FIRST_LIVE_READ_REPORT.md), [the P2 plan](docs/P2_PLAN.md), and [P2 readiness](docs/P2_READINESS.md).

Run the non-connecting live-pilot readiness check with `python -B scripts/preflight_p2_live_pilot.py`. A blocked exit is expected until the exact target, local credential reference, fixed owner authorization, and live policy are deliberately configured.

## P3 boundary

P3 coordinates exact-target routing, bounded declared adjacency, evidence validation, read-only evidence objectives, reasoning state, and a compact AI handoff across Ministry domains. It makes no live connection. Its policy accepts at most two fresh, scoped P2 FortiGate evidence records through the governed in-memory provenance envelope; it rejects stale, simulated, wrong-target, or malformed input. See [the P3 plan](docs/P3_PLAN.md), [P3 readiness](docs/P3_READINESS.md), [the offline pilot report](docs/P3_OFFLINE_PILOT_REPORT.md), and [the first P3/P4 live-evidence session](docs/P3_P4_LIVE_EVIDENCE_SESSION_REPORT.md).

## P4 boundary

P4 adds a schema-validated incident-intake form and `/api/incidents/intake` endpoint, provisional priority, sole-owner control, safe case continuation, evidence-objective gating, and a bounded handoff packet. A read-only governance endpoint exposes `OWNER_CONTROLLED`, `MNE-BRAIN-OWNER`, in-memory audit, no retention, and disabled automation. Read-only troubleshooting requires the owner's explicit `proceed`; changes and remediation require explicit owner instructions. P4 does not verify impact, invent an SLA, notify, ticket, page, auto-assign, auto-remediate, or persist case data. See [the P4 plan](docs/P4_PLAN.md), [P4 readiness](docs/P4_READINESS.md), [the original offline pilot](docs/P4_OFFLINE_PILOT_REPORT.md), [the professional intake report](docs/P4_INCIDENT_INTAKE_REPORT.md), and [the sole-owner governance report](docs/P4_WORKFLOW_GOVERNANCE_REPORT.md).

## P5 boundary

P5 adds 12 schema-governed troubleshooting runbooks, deterministic metadata-only selection, a dedicated Cisco FMC/FTD path, 48/48 context and owner-reviewed procedure coverage, P4 handoff guidance, a read-only API, and a GUI readiness view. Review means the procedure is suitable for bounded troubleshooting; it does not verify current health or authorize collection. See [the P5 plan](docs/P5_PLAN.md), [P5 readiness](docs/P5_READINESS.md), [the review report](docs/P5_OPERATIONAL_REVIEW_REPORT.md), and [the P5 pilot report](docs/P5_OFFLINE_PILOT_REPORT.md).

## P6 boundary

P6 adds 15 schema-governed read-only connector families covering 48/48 canonical entities across FortiGate, Cisco switching/routing/FMC/FTD, F5, Windows AD/DNS, Exchange, VMware, storage, Veeam, web/Linux applications, and printers. Plans contain fingerprints rather than raw operations, and every entity passes trust-0 injected transport validation. P7 live transports remain separately owner-gated and disabled at rest. See [the P6 plan](docs/P6_PLAN.md), [P6 readiness](docs/P6_READINESS.md), and [the P6 pilot report](docs/P6_OFFLINE_PILOT_REPORT.md).

## Local development server

```powershell
python core/api/server.py
```

First configure the only GUI owner, then start the loopback server:

```powershell
python scripts/configure_owner_login.py
python core/api/server.py
```

Open `http://127.0.0.1:8080` and sign in. The password is never stored in plaintext; the setup command stores a PBKDF2-SHA256 verifier in the OS keyring when available, otherwise in the ignored local environment file. Five failed logins lock the local login for five minutes. The server binds to `127.0.0.1`, allows one owner session, requires same-origin CSRF and one-time nonces for mutations, and expires idle sessions after 30 minutes.

Before startup, run `codex login status`. If the workstation's global Codex configuration contains an unsupported service tier, the GUI safely launches only its child App Server with `service_tier="fast"`; it does not rewrite the global configuration. The readiness card verifies the binary, ChatGPT session, App Server initialization, discovered Git root, sandbox, approval policy, and non-secret P7/P10 prerequisites. Set `MNE_BRAIN_PORT` to choose another loopback port; a conflict now fails clearly instead of silently choosing a different port.

## P10 boundary

The GUI presents the server-built exact target, vendor commands/API request, risk, expected impact, independent post-checks, rollback, and per-platform blockers before accepting an exact phrase. Real drivers require exact P7 binding/target identity, separate P10 credentials, a read-only privilege probe, fresh state, one single-use approval, one submission, and independent postchecks. Global infrastructure execution remains disabled at rest, and the server never treats read access, a blocked driver, or a mock as a live write.

## P11 boundary

New GUI conversations select Codex App Server when readiness is green and otherwise fall back explicitly to the limited deterministic provider. The Codex child receives a sanitized mirror without `.env`, VCS state, private keys, credential files, or inherited provider/device secrets. Safe mirror reads and validators can run automatically. Untrusted commands and every real repository diff pause for the server's exact preview and owner-session-bound single-use approval. Direct SSH, REST, WinRM, SNMP, database, or similar infrastructure commands are declined; live reads must use P7 and writes must use P10. Workspace rollback is separately prepared and approved.

### Automatic exact P7 live reads

1. Keep `p7_live_reads_enabled: false`. The server uses only the five-minute owner-scoped path enabled by `p7_owner_scoped_live_reads_available: true`.
2. Put the exact target, username, password, and trusted SSH host-key pin in the ignored external credential environment file referenced by `MNE_FORTIGATE_CREDENTIAL_ENV_FILE`. For the Tulkarm switch use the four `MNE_SWITCH_TULKARM_*` names in `.env.example`; for the router use `MNE_ROUTER_TULKARM_*`. Never enroll a first-seen key automatically.
3. Restart the server, sign in, and ask an exact question such as `what is the ip of tulkarm switch` or `what is the ip of tulkarm router`.
4. The server resolves one canonical entity to one active read-only P7 binding and runs it automatically under the authenticated session. No extra read popup is used.
5. Treat the answer as live only when it says `verified now` and the tool event contains fresh trust-5 evidence. Missing configuration, identity mismatch, authentication failure, timeout, or rejected output returns an unverified result and is not retried automatically.

### Configure the OpenCode secondary engine

1. Install OpenCode for the same Windows user that runs the GUI: `npm install -g opencode-ai`.
2. Restart `python core/api/server.py`. The application starts `opencode serve` on a random `127.0.0.1` port with a generated in-memory Basic Auth password and verifies `/global/health`.
3. Open `http://127.0.0.1:8080`, sign in, open Settings, and use the provider methods reported by OpenCode: API key, OAuth/device flow, an environment reference, or a validated custom OpenAI-compatible endpoint.
4. Refresh the live catalog, create a conversation, select **OpenCode**, then choose an exact connected provider/model. The choice is pinned after the first turn and never silently falls back.
5. OpenCode native shell, edits, and ungoverned tools are denied. Workspace reads and P7/P10 preparation cross the server-side ToolBroker; P10 approval and execution remain in the existing owner-controlled GUI.

See [the OpenCode engine guide](docs/P11_OPENCODE_ENGINE.md) for lifecycle, provider authentication, custom endpoints, security, direct terminal use, testing, and troubleshooting.
# Owner Direct primary mode

The authenticated owner console now defaults to `OWNER_DIRECT`: direct registered, exact read-only discovery gathers unverified identity evidence rather than requiring a stored pin. Device and service changes are prepared as one exact operation with a complete risk warning, then sent only by the GUI final-confirmation control. See [Owner Direct operator guide](docs/OWNER_DIRECT_MODE.md).
