# Security Agent Capabilities and AI Troubleshooting Execution Plan

> **Date:** 2026-09-09  
> **Target:** `MNE_Brain_v2`  
> **Implementation model:** Moderate-capability coding model such as Gemini Flash 3.8  
> **Execution style:** Six coherent batches. Do not split the work into one-function or one-test turns.

## 1. Objective

Upgrade the existing GUI Security Agent from a synchronous fixed report generator into an interactive troubleshooting workspace that:

- runs selected collectors over a real requested time window;
- streams genuine progress and supports cancellation and targeted retry;
- exposes useful collector diagnostics instead of only success/failure;
- allows Codex, Antigravity, or both to analyze a run or incident;
- opens an incident as a continued AI troubleshooting conversation;
- tracks repeated incidents and changes between runs;
- produces executive and technical reports from the same normalized run data;
- reuses the current P8/P9 troubleshooting engines and existing provider harnesses.

This is an extension of the current subsystem, not a replacement. Existing schedule, recipients, report download, email test, and daily execution must continue working during the migration.

## 2. Fast execution rules for a moderate model

The implementation agent must follow these rules to avoid slow micro-iterations:

1. Work batch-by-batch. Read all files listed for a batch, make the complete coherent change, then run the batch validation once.
2. Do not create a separate turn for every class, endpoint, or test. A normal batch should contain several related files and their tests.
3. Add tests alongside each batch, but run focused tests after the complete batch rather than after every small edit.
4. Preserve the current API routes until the replacement path is complete. Adapt old routes to the new service instead of breaking the GUI midway.
5. Use dependency injection for collectors, clock, run storage, and AI clients so tests never require live infrastructure or real email.
6. Do not execute the current live-calling `test_run_security_pipeline_dry_run` during ordinary validation. Replace it with injected fake collectors in Batch 1.
7. Keep GUI code presentational. Job state, progress, run calculations, incident lifecycle, and AI request construction belong in Python.
8. Store transient run artifacts under `operations/security_review/`; do not place runtime state in `config/security_agent_config.json`.
9. Use schemas for all new API and persisted contracts.
10. Do not add a new permission or confirmation system. Reuse the existing authenticated owner session and provider engine integrations.
11. Before editing, run `git status --short` and preserve existing changes, especially `00_meta/01_naming_conventions.md` and `config/security_agent_config.json`.
12. Do not restart the running API service as part of implementation. Finish code and tests, then report that a restart is required to load the changes.

## 3. Current baseline

The implementation starts from these existing components:

- Seven collectors under `core/connectors/security/`.
- Correlation and severity rules in `core/security_review/engine.py`.
- Static troubleshooting commands in `core/security_review/playbooks.py`.
- HTML/PDF/email generation in `core/security_review/reporter.py`.
- CLI orchestration in `core/security_review/cli.py`.
- Scheduler and last-run configuration in `core/security_review/config.py`.
- Security Agent API handlers in `core/api/server.py`.
- Security Agent dialog in `gui/index.html` and `gui/scripts/providers.js`.
- Codex App Server integration in `core/codex/app_server.py`.
- Antigravity CLI integration in `core/antigravity/harness.py`.
- Conversation orchestration in `core/conversation/engine.py`.
- P8/P9 troubleshooting engines in `core/troubleshooting/`.

Known baseline limitations that this plan must remove:

- the Security Agent does not call Codex or Antigravity;
- the GUI run console is reconstructed after completion rather than streamed;
- `/api/v2/security-agent/run` blocks until the whole pipeline finishes;
- all collectors are always selected and `hours_back` is fixed at 24;
- several collectors ignore `hours_back` and retrieve only a small tail or fixed limit;
- run success is recorded as true even when a collector or email fails;
- incidents receive daily sequence identifiers and cannot be tracked across runs;
- the GUI has no incident drill-down, AI analysis, run history, or targeted retry.

## 4. Target architecture

```text
GUI Run Request
    -> SecurityReviewService
        -> Background Run Manager
            -> Selected Collectors
            -> Normalized Events + Collector Diagnostics
            -> Incident Correlation + Stable Fingerprints
            -> Run Store
            -> Optional AI Analysis Pack
                -> Codex Analyzer
                -> Antigravity Analyzer
                -> Comparison Result
            -> HTML/PDF/JSON/CSV Reports
        -> SSE Progress Stream
        -> Incident/P8/P9 Investigation Handoff
```

The new service becomes the single orchestration entry point for GUI, CLI, and scheduled execution. The CLI must stop constructing collectors and reports directly.

## 5. New contracts

Create these schemas under `00_meta/schemas/` before implementing the service:

### 5.1 `security-review-request.schema.json`

Required fields:

- `mode`: `QUICK`, `FULL`, or `DEEP`;
- `collector_ids`: one or more registered collector IDs;
- `start_time` and `end_time`, or `hours_back`;
- `analysis_engine`: `NONE`, `CODEX`, `ANTIGRAVITY`, or `BOTH`;
- `analysis_model`: optional exact model ID;
- `send_email`: Boolean;
- `report_formats`: subset of `HTML`, `PDF`, `JSON`, `CSV`.

Optional filters:

- categories;
- branches;
- source or destination addresses;
- usernames;
- maximum records per collector;
- only failed collectors from a prior run.

### 5.2 `security-collector-diagnostic.schema.json`

Fields:

- collector and canonical entity identifiers;
- stage: `CONNECTION`, `AUTHENTICATION`, `QUERY`, `PARSE`, or `COMPLETE`;
- status: `NOT_RUN`, `RUNNING`, `SUCCESS`, `PARTIAL`, `FAILED`, or `CANCELLED`;
- requested and observed time ranges;
- transport and source queried;
- fetched, parsed, ignored, malformed, and duplicate counts;
- newest and oldest source timestamps;
- pagination/cursor information;
- duration;
- stable diagnostic code;
- concise message and suggested next diagnostic action.

### 5.3 `security-review-run.schema.json`

Fields:

- stable `run_id`;
- request snapshot;
- overall state and current stage;
- created, started, and completed timestamps;
- per-collector diagnostics;
- incident counts;
- report artifacts;
- email result;
- analysis result references;
- warnings and failure summary.

Overall state calculation:

- `COMPLETED`: requested collectors completed and requested reports were generated;
- `PARTIAL`: at least one collector completed and at least one failed or was partial;
- `FAILED`: no requested collector produced usable data or report generation failed;
- `CANCELLED`: owner cancelled the run;
- email failure is recorded separately and must not erase successful collection results.

### 5.4 `security-analysis-pack.schema.json`

The pack must be compact and identical for Codex and Antigravity. Include:

- run summary;
- selected incidents;
- normalized supporting events;
- collector diagnostics;
- matching canonical entities;
- related documented adjacency;
- matching runbook metadata and focused excerpts;
- earlier occurrences and trend summary;
- explicit unknowns;
- source references.

Default maximum serialized size: 24,000 characters. A single-incident pack should normally stay below 12,000 characters.

### 5.5 `security-analysis-result.schema.json`

Fields:

- provider, engine, model, analysis ID, and timestamps;
- plain-language summary;
- affected systems, users, branches, and services;
- ranked hypotheses;
- observations supporting or contradicting each hypothesis;
- missing evidence;
- recommended next diagnostic checks;
- immediate troubleshooting actions;
- longer-term resolution suggestions;
- relevant CLI and GUI steps;
- confidence;
- source references;
- provider warnings or partial-result status.

### 5.6 `security-incident-record.schema.json`

Add a stable fingerprint based on normalized category, signature family, source device/entity, attacker/source identity, target identity, and branch. Separate it from the daily display ID.

Lifecycle fields:

- `NEW`, `RECURRING`, `INVESTIGATING`, `RESOLVED`, or `REOPENED`;
- first seen, last seen, occurrence count, and run references;
- peak and current severity;
- analyst notes;
- linked troubleshooting thread and P8/P9 session IDs;
- Codex and Antigravity analysis references.

## 6. Batch 1 — Runtime service, job state, and compatibility layer

### Goal

Replace the synchronous function as the system entry point with a reusable service and background run manager while keeping current CLI, scheduler, and API behavior available.

### Main files

- Add `core/security_review/service.py`.
- Add `core/security_review/jobs.py`.
- Add `core/security_review/run_store.py`.
- Add `core/security_review/contracts.py`.
- Refactor `core/security_review/cli.py`.
- Refactor `core/security_review/daily_job.py`.
- Update `core/api/server.py`.
- Add schemas from Section 5.
- Add `tests/security_review/test_service_and_jobs.py`.
- Refactor `tests/security_review/test_cli_and_job.py` to use fake collectors and temporary output/config directories.

### Required behavior

`SecurityReviewService` must accept injected collector registry, reporter, run store, AI analyzer, clock, and executor. It owns the pipeline stages:

1. validate request;
2. create run;
3. execute selected collectors;
4. correlate incidents;
5. persist normalized run artifacts;
6. optionally request AI analysis;
7. generate requested reports;
8. optionally email;
9. finalize the run state.

`SecurityReviewJobManager` must:

- run reviews outside the HTTP request thread;
- reject duplicate starts for the same run ID;
- expose current state and progress events;
- support cancellation checkpoints between collectors and stages;
- retain a bounded in-memory event buffer for SSE reconnects;
- support targeted retry by creating a new run linked to the original.

`SecurityReviewRunStore` must write one directory per run:

```text
operations/security_review/runs/<run_id>/
    request.json
    run.json
    collector_diagnostics.json
    events.json
    incidents.json
    analyses/
    reports/
```

Use atomic JSON writes. The run store must list recent runs without reading every large report into memory.

### API additions

- `POST /api/v2/security-agent/runs` — start and immediately return `202` plus `run_id`.
- `GET /api/v2/security-agent/runs` — recent run summaries.
- `GET /api/v2/security-agent/runs/{run_id}` — current run.
- `GET /api/v2/security-agent/runs/{run_id}/events` — SSE progress.
- `POST /api/v2/security-agent/runs/{run_id}/cancel` — request cancellation.
- `POST /api/v2/security-agent/runs/{run_id}/retry` — retry failed/selected collectors.

Keep `POST /api/v2/security-agent/run` as a compatibility route that creates a full run. Update the old caller after the new GUI is complete.

### Acceptance

- Starting a run returns in under one second with a run ID when fake collectors are used.
- Progress events arrive in stage order.
- Cancellation stops before the next stage and persists `CANCELLED`.
- One failed collector produces `PARTIAL`, not unconditional success.
- CLI, scheduled job, and API use the same service.
- No test contacts infrastructure, SMTP, Codex, or Antigravity.

### Validation

```powershell
python -m pytest tests/security_review/test_service_and_jobs.py tests/security_review/test_cli_and_job.py tests/security_review/test_api_endpoints.py -q
python -m json.tool 00_meta/schemas/security-review-request.schema.json > $null
python -m json.tool 00_meta/schemas/security-review-run.schema.json > $null
```

## 7. Batch 2 — Genuine GUI progress and run controls

### Goal

Turn the current modal into an operational console using the new job API.

### Main files

- Update `gui/index.html`.
- Split Security Agent code out of `gui/scripts/providers.js` into new `gui/scripts/security_agent.js`.
- Update `gui/styles/main.css`.
- Update `core/api/server.py` only where required by the finalized GUI contract.
- Add or extend GUI contract tests.

### GUI structure

Add five tabs or panels within the existing dialog:

1. **Overview** — current counts, last run, collector status, schedule.
2. **Run Review** — scope, time, collectors, categories, report and AI options.
3. **Incidents** — searchable incident table and drill-down.
4. **AI Analysis** — Codex, Antigravity, and comparison results.
5. **History** — prior runs and report downloads.

### Run Review controls

- Quick/Full/Deep mode.
- Time window presets and custom start/end.
- Select all or individual collectors.
- Category filters.
- Analysis engine selector: None, Codex, Antigravity, Both.
- Exact available model list for the selected engine.
- Send-email toggle.
- Report-format selection.

### Real progress console

Render only server events. Show:

- run stage;
- collector currently executing;
- fetched/parsed/ignored counts;
- elapsed time;
- diagnostic messages;
- report and email stages;
- AI provider progress;
- final state.

Add Cancel, Retry Failed, Run Again, and Open Results controls. Reconnect SSE using the last received event sequence so dialog close/reopen does not lose progress.

Remove hard-coded statements such as “execution finished successfully” unless the server run state actually says `COMPLETED`.

### Acceptance

- The browser remains responsive throughout a run.
- Closing and reopening the dialog reconnects to the active run.
- Partial and failed collectors are visibly distinct.
- Cancel and Retry Failed work with fake delayed collectors.
- No risk, severity, or run-state calculation exists in JavaScript.

### Validation

```powershell
node --check gui/scripts/security_agent.js
node --check gui/scripts/providers.js
python -m pytest tests/security_review/test_api_endpoints.py tests/test_gui_contract.py -q
```

If `tests/test_gui_contract.py` does not exist, create a focused contract test that checks required element IDs and script loading rather than trying to reproduce browser behavior in Python.

## 8. Batch 3 — Collector depth and troubleshooting diagnostics

### Goal

Make requested time windows real, broaden useful data sources, and make empty or failed results explainable.

### Shared collector changes

Update:

- `core/connectors/security/base.py`;
- `core/connectors/security/models.py`;
- every collector under `core/connectors/security/`;
- collector tests and fixtures.

Introduce a common collector request containing start/end, filters, maximum records, mode, and cancellation callback. Return a diagnostic object with the events.

Separate these stages inside every collector:

1. connect;
2. authenticate;
3. query;
4. paginate/read;
5. parse;
6. normalize.

An empty successful query must say whether the source returned zero records, records were filtered by time/category, or records were present but unparseable.

### Collector-specific expansion

#### FortiGate

- Apply a real time range.
- Support disk event, VPN, IPS/UTM, antivirus, web-filter, and administrator/config events.
- Page results until the requested limit or source exhaustion.
- Capture policy ID, VDOM, interface, service, application/signature, source/destination ports, user, and device name when available.
- Record which transport was used and whether a fallback occurred.

#### FortiAnalyzer

- Replace the four-second real-time sample as the main source with bounded historical log search.
- Support ADOM, device/branch, category, and time filters.
- Poll asynchronous log-search tasks until complete or timeout.
- Page results and report total available versus retrieved.
- Preserve the originating firewall and ADOM.

#### F5 BIG-IP

- Query the requested interval instead of `tail -n 100` as the only mechanism.
- Collect ASM/AWAF request violations, policy/support IDs, enforcement action, virtual server, pool/member health, and certificate inventory.
- Parse source timestamps rather than replacing them with current time.
- Distinguish WAF incidents, TLS problems, pool problems, and device subsystem errors.

#### Cisco FMC

- Add actual intrusion-event retrieval in addition to audit records.
- Include Security Intelligence, malware/file, connection, deployment, and sensor-health events when supported.
- Handle domain discovery and pagination rather than relying on a fixed domain UUID or limit 50.
- Preserve rule, policy, intrusion signature, impact, action, source/destination, and managed-device identity.

#### Sophos Email

- Add quarantine, malware/sandbox, phishing/spoofing, DKIM/SPF/DMARC, delivery/reject, and service-health sources.
- Query by timestamp and paginate or read rotated logs as appropriate.
- Preserve sender, recipients, subject hash/identifier, message ID, verdict, rule, and disposition.

#### Active Directory

- Apply a `StartTime`/`EndTime` filter.
- Expand useful identity events: successful/failed authentication, lockout, privileged membership change, account creation/disable/reset, Kerberos failures, and policy changes.
- Extract named XML event fields instead of depending on the display message.
- Do not swallow PowerShell errors and return success with zero events.

#### Exchange

- Add message tracking, transport, OWA/ECP authentication, mailbox audit, queue/service, certificate, and connector events.
- Keep Windows Security events separate from message tracking rather than parsing both through one generic method.
- Apply a real time range and return per-source diagnostics.

### Parallelization

After the shared model/base change is complete, a moderate model may implement collectors in three independent groups:

- Group A: FortiGate + FortiAnalyzer;
- Group B: F5 + FMC;
- Group C: Sophos + AD + Exchange.

Merge the groups, then run all collector tests once.

### Acceptance

- Every collector test proves the requested time range appears in its query.
- Pagination stops at the configured maximum.
- Source timestamps survive normalization.
- Connection, authentication, query, and parse failures have different diagnostic codes.
- Zero-event success contains a useful explanation.
- Existing parsing fixtures continue passing.

### Validation

```powershell
python -m pytest tests/security_review/test_models_and_base.py tests/security_review/test_perimeter_collectors.py tests/security_review/test_appliance_collectors.py tests/security_review/test_identity_collectors.py tests/security_review/test_fortianalyzer_collector.py -q
```

## 9. Batch 4 — Incident lifecycle and interactive troubleshooting data

### Goal

Create stable incidents that can be searched, compared, reopened, and used by AI analysis.

### Main files

- Refactor `core/security_review/engine.py`.
- Add `core/security_review/incidents.py`.
- Add `core/security_review/trends.py`.
- Update `core/connectors/security/models.py`.
- Update `core/security_review/run_store.py`.
- Add incident API handlers to `core/api/server.py`.
- Update incident views in `gui/scripts/security_agent.js`.
- Expand `tests/security_review/test_risk_engine.py`.
- Add `tests/security_review/test_incident_lifecycle.py`.

### Correlation improvements

Do not collapse unrelated threats merely because they share an attacker IP and category. The grouping fingerprint must include a normalized threat/signature family and meaningful target scope.

Preserve:

- all devices and branches involved;
- all affected targets;
- all observed dispositions;
- supporting event IDs;
- earliest/latest observation;
- distinct signature and rule IDs;
- blocked versus allowed counts;
- the reason severity was assigned.

Make action normalization case-insensitive and explicit. Do not force every unmatched event to Medium; support Low and Informational results without filling the incident list with noise.

### Incident APIs

- `GET /api/v2/security-agent/incidents` with filters and pagination.
- `GET /api/v2/security-agent/incidents/{fingerprint}`.
- `POST /api/v2/security-agent/incidents/{fingerprint}/status`.
- `POST /api/v2/security-agent/incidents/{fingerprint}/notes`.
- `GET /api/v2/security-agent/incidents/{fingerprint}/timeline`.

### GUI incident drill-down

Show:

- summary and lifecycle;
- affected assets/users/branches;
- event timeline;
- supporting source records;
- earlier occurrences;
- collector gaps;
- static playbook;
- Codex and Antigravity analysis;
- buttons for Analyze, Compare, Open in Chat, and Start Troubleshooting.

### Acceptance

- The same recurring incident keeps one fingerprint across multiple run dates.
- Different exploit signatures or targets are not merged just because the IP matches.
- Incident state and notes survive process restart.
- Search and filter operate from compact indexes rather than loading all events.

### Validation

```powershell
python -m pytest tests/security_review/test_risk_engine.py tests/security_review/test_incident_lifecycle.py -q
```

## 10. Batch 5 — Codex and Antigravity analysis bridge

### Goal

Make Codex and Antigravity first-class analysis engines inside the Security Agent.

### Main files

- Add `core/security_review/analysis_pack.py`.
- Add `core/security_review/ai_analyzer.py`.
- Add `core/security_review/analysis_compare.py`.
- Update `core/security_review/service.py`.
- Update `core/conversation/engine.py` with a supported preloaded evidence/context entry point.
- Update `core/codex/app_server.py` only if required to pass the pack directly.
- Update `core/antigravity/harness.py` to remove hard-coded displayed version text and accept the same structured pack.
- Update `core/api/server.py`.
- Update `gui/scripts/security_agent.js`.
- Add `tests/security_review/test_analysis_pack.py`.
- Add `tests/security_review/test_ai_analyzer.py`.
- Extend `tests/test_p11_codex_app_server.py` and `tests/test_antigravity_engine.py`.

### Provider integration design

Do not duplicate provider process management. `SecurityAIAnalyzer` must call the existing ConversationEngine/Codex/Antigravity integration through a narrow adapter.

Provide these operations:

- analyze a complete run;
- analyze one incident;
- analyze selected incidents;
- ask a follow-up using an existing analysis conversation;
- compare existing Codex and Antigravity results;
- open the investigation as a normal GUI chat thread pinned to the chosen engine.

### Codex handling

Pass the current analysis pack directly with the turn. Do not rely on the Codex sanitized workspace already containing a newly generated run, because the mirror may have been created earlier.

Include a focused instruction telling Codex to:

- use the supplied pack as the primary run evidence;
- inspect relevant repository runbooks or code when useful;
- separate observations, hypotheses, and missing information;
- return the structured analysis result contract.

### Antigravity handling

Pass the identical pack and task instruction. Continue using the selected exact model. Obtain the CLI version dynamically for labels and progress messages.

### Both-engine mode

Run Codex and Antigravity concurrently after the pack is built. Persist each result independently. Comparison logic should produce:

- common conclusions;
- Codex-only conclusions;
- Antigravity-only conclusions;
- conflicting conclusions;
- diagnostics both recommend;
- unresolved questions.

The comparison layer organizes provider output; it must not invent a third conclusion without source references.

### API additions

- `POST /api/v2/security-agent/runs/{run_id}/analyses`.
- `POST /api/v2/security-agent/incidents/{fingerprint}/analyses`.
- `GET /api/v2/security-agent/analyses/{analysis_id}`.
- `GET /api/v2/security-agent/analyses/{analysis_id}/events` for progress.
- `POST /api/v2/security-agent/analyses/compare`.
- `POST /api/v2/security-agent/incidents/{fingerprint}/open-chat`.

### Acceptance

- Fake Codex and Antigravity adapters receive byte-equivalent analysis packs.
- A failed provider does not discard the other provider's successful result.
- Partial streamed answers are marked partial, not complete.
- Results validate against `security-analysis-result.schema.json`.
- Open in Chat creates a thread containing run/incident context and source references.
- The UI shows the actual provider version, model, state, and diagnostics.

### Validation

```powershell
python -m pytest tests/security_review/test_analysis_pack.py tests/security_review/test_ai_analyzer.py tests/test_p11_codex_app_server.py tests/test_antigravity_engine.py -q
```

## 11. Batch 6 — P8/P9 handoff, reporting, history, and final integration

### Goal

Complete the troubleshooting workflow and expose useful historical comparison without creating a second orchestration system.

### Main files

- Add `core/security_review/troubleshooting_bridge.py`.
- Update `core/troubleshooting/engine.py` and `core/troubleshooting/p9_engine.py` only through public integration methods.
- Update `core/security_review/reporter.py` and template.
- Update `core/security_review/trends.py`.
- Update `core/security_review/config.py` for reusable review profiles and multiple schedules if desired.
- Complete Security Agent API and GUI history views.
- Add end-to-end fixture tests.
- Update subsystem documentation.

### Troubleshooting handoff

“Start Troubleshooting” must:

1. resolve one exact canonical entity from the incident;
2. create a compact handoff containing the incident fingerprint, accepted source observations, unknowns, and recommended checks;
3. ask P8 for a bounded troubleshooting plan;
4. allow P9 execution only through its existing interface;
5. link resulting sessions and evidence back to the incident timeline;
6. allow Codex or Antigravity to analyze the new evidence in the same investigation.

Do not copy P8/P9 logic into `security_review`.

### Reporting enhancements

Generate all formats from the persisted run and incident records rather than recalculating from live objects.

Add:

- executive report;
- technical report;
- JSON export;
- CSV incident export;
- new, recurring, increased, decreased, and no-longer-observed sections;
- collector coverage and data-gap section;
- Codex/Antigravity analysis summaries with source references;
- seven-day and thirty-day trend charts or tables;
- per-device query and parsing health trends.

### Review profiles

Support named profiles such as:

- `Daily Full Review`;
- `Quick Perimeter Check`;
- `Identity Investigation`;
- `Email Threat Review`;
- `Branch Investigation`.

A profile stores run request options, not credentials. The current daily schedule migrates to `Daily Full Review` automatically.

### End-to-end fixture scenario

Create one complete test scenario containing:

- FortiGate VPN failures;
- matching F5 exploit attempt;
- one FMC intrusion record;
- an AD lockout;
- one failed collector;
- recurring data from a previous run;
- fake Codex and Antigravity outputs;
- generated HTML/PDF/JSON/CSV artifacts.

The test must prove:

- real progress ordering;
- `PARTIAL` final state;
- stable incident recurrence;
- both-engine comparison;
- report generation;
- P8 handoff payload;
- no live transports or SMTP calls.

### Validation

```powershell
python -m pytest tests/security_review tests/test_antigravity_engine.py tests/test_p11_codex_app_server.py -q
python -m pytest tests/test_p8_phase.py tests/test_p9_phase.py -q
python -m pytest -q
git diff --check
```

If exact P8/P9 test filenames differ, discover them with `rg --files tests | rg "p8|p9"` and use the existing focused suites.

## 12. Recommended delivery sequence and parallel work

```text
Batch 1: Service + jobs + schemas
    |
    +--> Batch 2: GUI progress and controls
    |
    +--> Batch 3: Collector upgrades
             |
             +--> Batch 4: Incident lifecycle
                      |
                      +--> Batch 5: Codex/Antigravity bridge
                               |
                               +--> Batch 6: P8/P9 + reports + final integration
```

Fastest reasonable execution:

- Complete Batch 1 first.
- Run Batch 2 and the three Batch 3 collector groups in parallel if multiple agents are available.
- Merge and validate before Batch 4.
- Batch 5 may begin once the analysis-pack schema and stable incident model are final.
- Batch 6 is the only full integration batch.

For a single moderate model, use one turn per batch, with Batch 3 allowed two turns if context becomes too large. The expected implementation is six or seven substantial turns, not dozens of micro-turns.

## 13. Definition of done

The enhancement is complete only when:

- GUI runs are asynchronous and show genuine streamed progress;
- owners can choose devices, time range, categories, report formats, and AI engine;
- collectors honor requested ranges and expose detailed diagnostics;
- failed collectors can be retried independently;
- incidents retain stable identity and history across runs;
- Codex and Antigravity can analyze the same run or incident pack;
- both-engine comparison and follow-up chat work;
- an incident can start and receive results from P8/P9 troubleshooting;
- reports include technical detail, trends, and collection gaps;
- scheduled and CLI runs use the same service as the GUI;
- focused and full automated suites pass without contacting live infrastructure;
- existing unrelated worktree changes remain intact;
- the final handoff identifies whether the running API service still needs an owner-confirmed restart.

## 14. Final handoff format for every batch

The implementation model should finish each batch with one compact report:

```text
Batch completed:
Files added/changed:
Behavior delivered:
Tests run and result:
Known remaining work:
Runtime restart required: yes/no
```

Do not provide a long narration of every edit. Report the completed capability and validation result.
