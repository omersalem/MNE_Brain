Created At: 2026-07-27T07:12:00Z
Completed At: 2026-07-27T10:15:00Z
File Path: `file:///d:/projects/MNE_Brain/MNE_Brain/plan.md`

No repository files were changed. Below is an execution roadmap designed for a medium-capability AI: each phase is small, deterministic, and independently testable.

Refined Architecture Flow

Question
   ↓
Deterministic Query Router
   ↓
Entity Resolution (only if required)
   ↓
Evidence Pack Builder
   ↓
AI Reasoning & Investigation Planning Engine (Phase D.5)
   ↓
Optional Read-Only Live Verification
   ↓
Route-Specific Structured Answer
   ↓
Controlled Remediation

Python remains limited to indexing, normalization, routing, evidence construction, and policy enforcement. It must never determine root cause, choose remediation, or perform investigation planning.
The AI remains responsible for reasoning, investigation planning, diagnosis, decision making, and explanation.

Phase A — Repository integrity and security

Objective: Make repository content trustworthy before improving retrieval.

Why: Current duplicate documents and simulated “VERIFIED” discovery reports can cause incorrect answers and unsupported claims.

Create
00_meta/03_ai_contracts/status-vocabulary.yaml
00_meta/03_ai_contracts/metadata-schema.yaml
00_meta/03_ai_contracts/canonical-content-policy.md
operations/quality/.gitkeep
scripts/audit_repository.py

Modify
AGENTS.md
agents/base-agent.md
scripts/run_discovery.py
tasks/discover-*.md
profiles/*.yaml
All canonical notes under knowledge/
.gitignore
.github/workflows/*.yml

Delete
Only exact duplicate files listed in an approved generated manifest.
Do not delete manually or by filename similarity.

Implementation steps
Define allowed status values:
documented: meaning: "Supported by canonical repository knowledge."
live_verified: meaning: "Supported by successful read-only evidence with timestamp."
stale: meaning: "Known information is older than its freshness policy."
unverified: meaning: "Claim exists but has no accepted evidence."
failed: meaning: "A requested check failed; no conclusion is permitted."
not_run: meaning: "No live check was performed."

Remove all hard-coded VERIFIED, success, trust-score, and zero-drift claims from discovery scripts and reports.
Make run_discovery.py emit not_run unless actual evidence is supplied by an adapter.
Define required frontmatter: id, type, aliases, owner, source, trust_tier, last_verified, related_entities.
Implement audit_repository.py to report:
- exact duplicate hashes;
- missing required frontmatter;
- broken wiki links;
- invalid status values;
- plaintext-secret patterns;
- stale live-evidence references.

Generate operations/quality/repository-audit-YYYY-MM-DD.md.
Create a reviewed canonical-map.yaml before deleting duplicates. Each duplicate must map to one canonical file or an archive reason.
Remove plaintext credentials from connection profiles; replace values with secret references such as secret_ref: MNE_FORTIGATE_READONLY_PASSWORD.
Rotate exposed secrets outside the repository before any future live execution.
Stop workflow auto-pushes to main; create reports in a branch or require approval.

Validation checklist
- audit_repository.py exits non-zero on fake live_verified claims.
- No plaintext password/token/key pattern is found.
- Every active canonical document has required metadata.
- Duplicate report contains a canonical decision for every duplicate.
- A failed discovery cannot produce live_verified.

Rollback
Restore deleted duplicates from Git.
Retain the canonical map and audit report even after rollback.
Revert workflow changes if CI cannot complete, but do not restore plaintext secrets.

Completion criteria
No unsupported verified claims.
No secrets in tracked documents.
One canonical owner per retained knowledge item.

Difficulty: Medium.
Dependency: None.

Phase B — Lightweight entity resolution

Objective: Resolve infrastructure entities when required by the Query Router.

Why: Entity Resolution is invoked only when a request references specific assets (IP, hostname, VIP, device). Generic concept questions (e.g. "Explain Exchange DAG", "How does OSPF work?") bypass this step entirely to eliminate unnecessary overhead.

Create
00_meta/03_ai_contracts/entity-index-schema.yaml
00_meta/03_ai_contracts/entity-resolution-rules.yaml
00_meta/04_indices/entity-index.json
scripts/build_entity_index.py
operations/quality/entity-index-report-YYYY-MM-DD.md

Modify
Canonical files under knowledge/
00_meta/04_indices/master-dashboard.md
skills/search/skill.md
agents/base-agent.md

Delete
None.

Implementation steps
Define one entity record:
{
  "id": "fw-fortigate-hq-01",
  "type": "firewall",
  "canonical_note": "knowledge/.../fw-fortigate-hq-01.md",
  "aliases": ["FG-MNE", "FortiGate HQ"],
  "ips": ["172.x.x.x"],
  "fqdns": ["example.internal"],
  "services": ["internet-egress", "ssl-vpn"],
  "site": "HQ",
  "vlans": [],
  "related_entities": ["sw-cisco-core-01"],
  "trust_tier": 3,
  "last_verified": "YYYY-MM-DD"
}

Support lookup fields: IP, hostname, FQDN, alias, device ID, service, application, branch, VLAN.
Execute entity resolution only when flagged as required by Phase D (Query Router).
Define deterministic ambiguity handling:
- one match: select it;
- multiple matches: return up to three candidates;
- zero matches: label target unknown; do not invent one.

Build the index only from canonical knowledge/ files.
Deduplicate aliases case-insensitively.
Reject duplicate entity IDs and conflicting IP ownership.
Add entity references to runbooks and incidents, rather than repeating full asset details.
Generate the index in stable sorted order so Git diffs remain small.

Validation checklist
- Lookup test cases resolve an IP, hostname, alias, branch, VLAN, and service.
- Conflicting aliases fail the build.
- The generated index contains no secrets or raw connection fields.
- Index links point only to existing canonical notes.
- Generic non-asset queries do not trigger entity resolution.

Rollback
Delete the generated index and revert metadata additions.
No knowledge document is deleted in this phase.

Completion criteria
Every primary asset has one searchable entity record.
Asset-focused questions resolve targets before document retrieval; concept questions bypass resolution cleanly.

Difficulty: Medium.
Dependency: Phase A & Phase D.

Phase C — Evidence-pack builder

Objective: Give the AI only the evidence needed for the specific query route and resolved entities.

Why: Retrieval size, not model intelligence, is the largest avoidable source of token waste and confused answers.

Create
00_meta/03_ai_contracts/evidence-pack-schema.yaml
00_meta/03_ai_contracts/evidence-selection-policy.yaml
scripts/build_evidence_pack.py
templates/evidence-pack.md
operations/evidence/.gitkeep
tests/fixtures/evidence-pack/

Modify
skills/search/skill.md
skills/explain/skill.md
skills/review/skill.md
agents/base-agent.md

Delete
None.

Implementation steps
Accept inputs: question, query_route, resolved_entity_ids (optional), and optional live_evidence_ids.
Build evidence packs in priority order:
1. canonical asset;
2. direct dependency;
3. relevant runbook;
4. relevant incident;
5. approved live evidence.

Tailor pack assembly to query route complexity:
- asset lookup: canonical asset only;
- topology: asset plus direct path dependencies;
- explanation: canonical concept notes and linked architecture notes;
- incident: asset, dependencies, one runbook, one most relevant incident;
- remediation: previous evidence plus approved action template and policy.

Extract only structured metadata and relevant document sections; never attach whole manuals by default.
Label every evidence item with source, trust_tier, observed_at, and freshness.
Return an explicit unknowns array when no accepted evidence exists.
Never convert a document claim into live evidence.
Store live raw output separately and expose only normalized evidence fields.

Validation checklist
- Simple lookup produces one canonical asset item.
- Explanation query includes conceptual evidence without requiring asset entities.
- Incident pack includes no unrelated manuals.
- A stale document is labeled stale.
- Missing evidence appears in unknowns.
- Pack builder never labels a document as live evidence.

Rollback
Disable evidence-pack generation and retain existing direct document search.
Keep schemas and fixtures for later correction.

Completion criteria
The model receives focused, attributable evidence tailored to the query route rather than vault-wide context.

Difficulty: Medium.
Dependency: Phase B and Phase D.

Phase D — Deterministic query router

Objective: Select the right task route and determine if entity resolution is required as the first step for every request.

Why: The router acts as the entry point for all questions. By identifying non-asset queries upfront (e.g. concept explanations), it bypasses Entity Resolution, saving processing steps and token usage.

Create
00_meta/03_ai_contracts/query-routing-rules.yaml
00_meta/03_ai_contracts/query-route-schema.yaml
scripts/route_query.py
tests/fixtures/query-routing/

Modify
agents/base-agent.md
agents/codex.md
tasks/*.md
skills/README.md

Delete
None.

Supported routes
Route | Required evidence | Entity Resolution Required
--- | --- | ---
Asset lookup | Canonical asset | Yes
Topology | Asset and path dependencies | Yes
Explanation | Canonical facts and linked diagram/path notes | No
Incident | Asset, recent incident, known impact | Yes
Troubleshooting | Asset, dependencies, runbook, targeted checks | Yes
Health check | Asset and permitted live profile | Yes
Documentation | Canonical note and official manual if needed | Conditional
Review | Metadata, link, freshness, duplicate reports | Conditional
Remediation | Verified cause, action policy, approved template | Yes

Implementation steps
Use ordered YAML rules; no model-based route selection.
Execute as the initial entry point for every incoming question.
Match explicit action words and patterns first: check, health, down, fix, review, where, policy, explain.
Determine whether entity resolution is required (set `requires_entity_resolution: true/false`).
If `requires_entity_resolution` is false (e.g. "Explain Exchange DAG", "How does OSPF work?", "Explain FortiGate HA"), route directly to Evidence Pack Builder.
If `requires_entity_resolution` is true, invoke Entity Resolution (Phase B) before Evidence Pack Builder.
Route fix, change, restart, allow, and modify requests through remediation policy—not directly to an adapter.
Emit a compact route object with route, target, requires_entity_resolution, evidence_requirements, live_check_allowed, and remediation_gate_required.

Validation checklist
- Every benchmark question has one expected route.
- Questions like "Explain Exchange DAG" set `requires_entity_resolution: false` and bypass Phase B.
- Ambiguous requests return candidates or ask for a minimal identifier.
- Write-like requests always require the remediation gate.
- Generic explanations do not invoke live checks or entity resolution.

Rollback
Revert to existing task selection instructions.
Preserve route test fixtures.

Completion criteria
The same request produces the same route, entity requirement, and evidence specification.

Difficulty: Low to medium.
Dependency: Phase A.

Phase D.5 — Investigation Planning Engine

Objective: Build an explicit investigation plan before any live verification or diagnostic troubleshooting.

Why: Prevents direct, unplanned troubleshooting. Ensures the Brain systematically formulates hypotheses, ranks evidence by information gain, minimizes operational cost, and avoids unnecessary device queries.

Create
00_meta/03_ai_contracts/investigation-planner-spec.md
00_meta/03_ai_contracts/investigation-plan-schema.yaml
templates/investigation-plan.md
tests/fixtures/investigation-planning/

Modify
agents/base-agent.md
agents/codex.md
tasks/investigate.md

Delete
None.

Purpose & Core Responsibilities
The Investigation Planning Engine runs after the Query Router and Evidence Pack Builder for troubleshooting, incident, and health check routes. It performs reasoning ONLY and NEVER executes commands directly.

Key Responsibilities & Intelligence Capabilities:
- Live Verification Necessity: Determines if live verification is strictly required or if Knowledge Base evidence is sufficient.
- Unknown & Gap Analysis: Identifies missing facts and unknown variables prior to taking live action.
- Highest Information Gain Analysis: Evaluates candidate checks and selects the query/command that yields maximum diagnostic clarity.
- Evidence Ranking: Prioritizes single high-value observations over multiple low-value observations.
- Stop Early Principle: Establishes clear stop conditions and confidence thresholds to cease investigation early once proven.
- Observation vs Interpretation Separation: Maintains strict boundaries between raw observed facts and AI diagnostic interpretations.
- Confidence Evolution & Hypothesis Tracking: Tracks hypothesis verification and rejection confidence systematically.
- Investigation Decision Tree Generation: Maps out binary investigation strategies to halve the search space at each step.
- Operational Cost Minimization: Calculates and minimizes operational cost, number of live commands, and unnecessary device access.

Implementation steps
Define `investigation-plan-schema.yaml` with fields for hypotheses, evidence_required, device_query_sequence, expected_confidence_gain, operational_cost_estimate, and stop_conditions.
Integrate the planning engine into `tasks/investigate.md` and agent instructions.
Ensure the engine operates purely in AI reasoning space, producing a structured Investigation Plan before any read-only adapter execution.
Enforce the Stop Early Principle: if KB evidence meets confidence thresholds, mark live verification as unnecessary.

Validation checklist
- Plan is generated before any live adapter call is triggered.
- High-information-gain check is prioritized over broad polling.
- Operational cost and command count are minimized.
- Engine never executes commands or modifies state.
- Binary decision tree correctly specifies stop conditions.

Rollback
Bypass Phase D.5 and fall back to standard evidence pack evaluation.
Retain schemas and fixtures.

Completion criteria
Every complex troubleshooting request produces an optimal, cost-minimized investigation plan before live verification.

Difficulty: Medium.
Dependency: Phase D.

Phase E — Dynamic answer templates

Objective: Make answers concise, structured, and route-tailored.

Why: Fixed templates force irrelevant sections onto simple answers. Route-specific templates expose only high-value sections, keeping responses focused and token usage low.

Create
00_meta/03_ai_contracts/dynamic-answer-templates.md
00_meta/03_ai_contracts/confidence-policy.yaml
tests/fixtures/answer-output/

Modify
agents/base-agent.md
agents/codex.md
skills/search/skill.md
skills/explain/skill.md
tasks/remediate.md

Delete
None.

Route-Specific Response Templates

Explanation:
**Answer:** Concise concept summary.
**Related Components:** Primary linked architecture components.
**References:** Knowledge links.

Topology:
**Path:** End-to-end traversal sequence.
**Dependencies:** Direct component dependencies.
**Evidence:** [Documented | Live] structural source.

Asset Lookup:
**Asset Details:** Key metadata and IP/FQDN mapping.
**Status:** Documented status and freshness.
**References:** Canonical note reference.

Incident:
**Status:** Healthy | Degraded | Failed | Unknown
**Evidence:** Concise, attributable facts.
**Confidence:** High | Medium | Low
**Unknowns:** Key unresolved facts affecting conclusion.
**Next Check:** Highest information gain check.
**Action:** Required remediation or escalation step.

Troubleshooting:
**Status:** Healthy | Degraded | Failed | Unknown
**Diagnosis:** Root cause or active hypothesis.
**Evidence:** Supporting evidence list.
**Confidence:** High | Medium | Low
**Unknowns:** Unverified items.
**Recommended Next Check:** Single minimal check.

Health Check:
**Status:** Healthy | Degraded | Failed
**Telemetry:** Summary of key metrics / check results.
**Findings:** Active anomalies or clean confirmation.
**Next Check:** Routine or follow-up check if degraded.

Review:
**Item:** Target document or artifact.
**Metadata:** Owner, trust tier, last verified date.
**Findings:** Audit results, gaps, or compliance status.
**Freshness:** Current vs stale threshold.

Remediation:
**Proposal:** Intended change description.
**Target:** Affected entity ID.
**Risk Level:** Low | Medium | High
**Approval State:** Pending approval.
**Rollback Plan:** Step-by-step rollback procedure.
**Validation Plan:** Post-change verification check.

Implementation steps
Set target response lengths based on route complexity (e.g. 100–180 words for standard queries).
Enforce route-specific templates in `00_meta/03_ai_contracts/dynamic-answer-templates.md`.
Expose only sections that add value; omit irrelevant fields dynamically.
Require evidence and confidence in incident, troubleshooting, and health check answers.
Do not output raw command dumps unless explicitly requested.
Keep remediation outputs strictly as proposals until authorized.

Validation checklist
- Answers adhere to route-specific section templates.
- Explanation answers do not contain empty Status or Next Check fields.
- Incident and Troubleshooting answers enforce Evidence, Confidence, and Unknowns.
- Total token output is significantly reduced for simple routes.

Rollback
Revert agent template instructions to default formats.

Completion criteria
All responses use clean, route-tailored formatting that maximizes clarity while minimizing token usage.

Difficulty: Low.
Dependency: Phases C, D, D.5.

Phase F — Thin read-only adapters

Objective: Add truthful live verification without a large connector framework.

Why: Live access must collect evidence, not simulate it or embed troubleshooting logic in code.

Create
tasks/verify-live.md
00_meta/03_ai_contracts/live-evidence-schema.yaml
scripts/live_verify.py
scripts/adapters/fortigate_read.py
tests/fixtures/live-adapters/fortigate/

Modify
profiles/fortigate.yaml
config/action_policy.yaml
scripts/run_discovery.py
.github/workflows/network-discovery.yml

Delete
Retire simulated connector execution paths only after the FortiGate adapter succeeds.
Do not remove compatibility code until tests confirm no workflow depends on it.

Implementation steps
Define a generic live-verification request with: entity ID, approved check ID, read-only profile, correlation ID, timeout.
Execution plan is dictated by Phase D.5 (Investigation Planning Engine).
Define the FortiGate profile allow-list: system status, interface status, route lookup, policy lookup, VPN/SD-WAN health.
Implement the adapter with four responsibilities: obtain secret by reference, connect, execute allowed read operation, normalize and save evidence.
Save raw output under restricted operations/evidence/.
Emit normalized evidence with timestamp, command/check ID, target, result status, and evidence ID.
Treat authentication, timeout, authorization, and parsing errors as failed; never infer healthy state.
Ensure discovery reports summarize actual adapter outcomes only.
Add F5, Cisco, VMware, Windows, Linux, Exchange, and storage adapters one platform at a time after this pattern is accepted.

Validation checklist
- Adapter refuses any command not listed in the profile.
- A connection failure produces failed, not healthy.
- Evidence is timestamped and attributable.
- No credential appears in output, logs, Git, or reports.
- Discovery report is live_verified only when adapter evidence exists.

Rollback
Disable the adapter through its profile feature flag.
Preserve evidence files and report failures for audit.

Completion criteria
One complete FortiGate read-only verification path is real, bounded, and auditable.

Difficulty: Medium.
Dependency: Phases A, C, D, D.5.

Phase G — Benchmark scenarios

Objective: Measure answer quality and prevent regressions.

Create
benchmarks/README.md
benchmarks/scenarios.yaml
benchmarks/expected-results/
scripts/run_benchmarks.py
operations/quality/benchmark-report-YYYY-MM-DD.md

Modify
README.md
.github/workflows/ to add a benchmark workflow.

Delete
None.

Required scenarios
- DNS resolution mismatch
- FortiGate policy lookup
- F5 pool member unavailable
- Exchange mail-flow failure
- VMware VM unavailable
- SSL-VPN issue
- Branch outage
- Slow application
- Unknown hostname
- Stale documentation
- Unsupported remediation request

Each scenario must assert: expected route, expected resolved entity, permitted evidence sources, expected confidence ceiling, best next check, correct stop condition, no unsupported live or root-cause claim, no unsafe action proposal.

Implementation steps
Store only sanitized fixtures; never include production credentials or raw sensitive telemetry.
Start with ten scenarios and one expected result per scenario.
Test deterministic components automatically: routing, entity resolution, evidence packing, policy gates.
Review model output against a small rubric rather than exact wording.
Fail a scenario if it claims live verification without live evidence or bypasses investigation planning rules.

Validation checklist
- All benchmark scenarios execute locally.
- No benchmark requires real infrastructure access.
- Regression report identifies the failing layer.

Rollback
Disable benchmark workflow if unstable; keep fixtures and reports.

Completion criteria
Every future change can be checked against representative infrastructure questions.

Difficulty: Medium.
Dependency: Phases B–F (including D.5).

Phase H — Continuous validation

Objective: Prevent knowledge and automation quality from degrading.

Create
scripts/validate_brain.py
.github/workflows/brain-validation.yml
operations/quality/validation-report-YYYY-MM-DD.md

Modify
All discovery workflows to run validation before publishing reports.
README.md
AGENTS.md

Delete
None.

Validation order
1. Secret scan
2. Metadata validation
3. Duplicate detection
4. Broken-link validation
5. Canonical-map validation
6. Entity-index build
7. Evidence-pack fixtures
8. Query-router fixtures
9. Investigation-planner fixtures
10. Dynamic answer-template fixtures
11. Benchmark suite
12. Discovery-report truthfulness checks

Implementation steps
Make validation read-only.
Use distinct exit codes for security, metadata, index, evidence, routing, investigation planning, and benchmark failures.
Publish a concise Markdown report suitable for human review.
Block workflow publication on security or truthfulness failures.
Run full validation on pull requests and a lighter audit nightly.
Track trend metrics: duplicate count, metadata completeness, broken links, stale assets, benchmark pass rate, average evidence-pack size, average normal answer length, unsupported claim count.

Validation checklist
- CI fails on a plaintext secret or fake verified status.
- CI fails on broken canonical references.
- CI fails when entity-index generation is non-deterministic.
- Validation report identifies the exact failing file and rule.

Rollback
Revert only the failing validator rule or workflow integration.
Do not bypass secret or verified-claim validation.

Completion criteria
Every repository change is continuously checked for truthfulness, retrieval quality, and safety.

Difficulty: Medium.
Dependency: Phases A–G (including D.5).

Strict implementation order
Phase A — Repository integrity and security
Phase D — Deterministic query router
Phase B — Lightweight entity resolution (invoked conditionally by Router)
Phase C — Evidence-pack builder
Phase D.5 — Investigation Planning Engine
Phase E — Dynamic answer templates
Phase F — Thin read-only adapters (FortiGate first)
Phase G — Benchmark scenarios
Phase H — Continuous validation
Add remaining live adapters individually

==================================================
SUMMARY OF ARCHITECTURAL REFINEMENTS
==================================================

1. Modified Execution Order
   1. Phase A — Repository integrity and security
   2. Phase D — Deterministic query router (Entry point for all requests)
   3. Phase B — Lightweight entity resolution (Executed only if query route requires asset identification)
   4. Phase C — Evidence-pack builder (Tailored retrieval based on query route)
   5. Phase D.5 — Investigation Planning Engine (AI-native reasoning for hypothesis formation and check planning)
   6. Phase E — Dynamic answer templates (Route-tailored structured outputs)
   7. Phase F — Thin read-only adapters (Targeted live verification as specified by Investigation Plan)
   8. Phase G — Benchmark scenarios (Validation suite)
   9. Phase H — Continuous validation (CI/CD pipeline integration)

2. New Architecture Diagram

Question
   ↓
Deterministic Query Router (Phase D)
   ├───> Concept / Generic Query (e.g. "Explain Exchange DAG")
   │        ↓
   │     Evidence Pack Builder (Phase C)
   │
   └───> Asset-Referencing Query (e.g. "Check FW-01 status")
            ↓
         Entity Resolution (Phase B)
            ↓
         Evidence Pack Builder (Phase C)
   ↓
AI Reasoning & Investigation Planning Engine (Phase D.5)
   ↓
Optional Read-Only Live Verification (Phase F - only if required by Investigation Plan)
   ↓
Route-Specific Dynamic Answer (Phase E)
   ↓
Controlled Remediation (Gate)

3. List of Changed Phases
   - Refined Architecture Summary: Replaced fixed linear flow with the Query Router entry point and Investigation Planning layer.
   - Phase B (Lightweight Entity Resolution): Modified to be invoked conditionally by the Query Router rather than on every query.
   - Phase C (Evidence-Pack Builder): Modified to accept inputs with optional resolved entity IDs and route-tailored context extraction.
   - Phase D (Deterministic Query Router): Moved to the first step of query execution; added logic to flag `requires_entity_resolution`.
   - Phase D.5 (Investigation Planning Engine): NEW PHASE inserted after Phase D/C. Implements hypothesis ranking, information gain analysis, Stop Early principle, and command minimization without direct execution.
   - Phase E (Dynamic Answer Templates): Replaced single fixed template with route-specific templates (Explanation, Topology, Asset Lookup, Incident, Troubleshooting, Health Check, Review, Remediation).
   - Phase F, G, H: Updated dependencies and validation order to include Phase D.5.
   - Strict Implementation Order: Reordered implementation sequence (Phase A -> D -> B -> C -> D.5 -> E -> F -> G -> H).

4. Why these improvements make the Brain better while keeping token usage low
   - Bypassing Entity Resolution for Concept Queries: Queries like "Explain Exchange DAG" or "How does OSPF work?" no longer trigger entity lookups or load asset metadata into context. This eliminates unnecessary index parsing and reduces context size.
   - Information-Gain Driven Investigation: Instead of running multiple broad live commands, Phase D.5 calculates the single highest-value observation to confirm or reject hypotheses. This prevents iterative, token-heavy diagnostic loops and reduces live device strain.
   - Stop Early Principle: Investigation planning defines clear stop conditions. Once KB evidence or a single live check reaches the required confidence threshold, investigation ceases immediately rather than gathering extraneous data.
   - Dynamic, Route-Specific Output Templates: Replacing a one-size-fits-all answer template with minimal, route-specific sections (e.g. 3 concise sections for explanations vs 6 for incidents) avoids generating empty or redundant boilerplate text, significantly saving output tokens.
   - Strict Separation of Concerns: Python handles deterministic work (routing, entity lookup, evidence slicing) fast and efficiently, while the AI focuses purely on high-level reasoning, investigation planning, and diagnosis.
