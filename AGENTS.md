# AGENTS.md — Supreme Repository Governance & Single Source of Truth (Release 2)

> **Mandatory Rule:** This document is the single source of truth for all repository governance, architecture contracts, safety rules, naming conventions, and engineering principles for **MNE_Brain Release 2 (`MNE_Brain_v2`)**. All AI Agents operating on this repository inherit 100% of their rules from this file.

---

## 1. 3-Layer Decoupled Repository Architecture

Release 2 strictly enforces the separation of permanent facts, operational state, and engineering experience across three dedicated directory layers:

- **Layer 1 `knowledge/`:** Permanent Infrastructure Facts (Topology, Canonical Notes, Devices, Profiles).
- **Layer 2 `operations/`:** Operational History & Transient Logs (Incidents, Discovery Reports, Live Verification Outputs, Action Audits).
- **Layer 3 `intelligence/`:** Reusable Engineering Experience (SOP Runbooks, Troubleshooting Guides, Best Practices).

---

## 2. Senior Infrastructure Engineer Operating Workflow

Every request or alert follows a 12-stage deterministic pipeline:

```
Question / Alert ➔ Incident Case Management ➔ Core Flow ➔ Incident Orchestration ➔ Runbook Intelligence ➔ Reasoning ➔ Policy ➔ Connector Routing ➔ Live Verification ➔ Knowledge Lifecycle ➔ Execution (If Needed) ➔ Evidence-Based Answer
```

1. **Incident Case Management (`core/incidents/`):** Normalizes reported impact, proposes an owner-confirmed priority, applies the sole owner `MNE-BRAIN-OWNER`, and maintains a non-persistent handoff packet.
2. **Core Flow (`core/router/`, `core/entity/`, `core/evidence/`):** Classifies intent, resolves hostnames/IPs, and builds token-bounded evidence context (**<1,500 tokens**).
3. **Incident Orchestration (`core/orchestration/`):** Requires an exact target, loads bounded documented adjacency, selects evidence objectives, and prepares a compact AI handoff without executing checks.
4. **Runbook Intelligence (`core/runbooks/`):** Selects at most three governed metadata-only candidates and keeps reviewed procedure coverage separate from live-state and production readiness.
5. **Reasoning Engine (`core/reasoning/`):** Evaluates hypothesis graph, calculates Information Gain ($H$), and enforces the **Stop Early Principle** (>95% certainty).
6. **Policy Engine (`core/policy/`):** Evaluates verification necessity, read-only policy, Level 0–4 risk gates, and operational constraints.
7. **Connector Routing (`core/connectors/`):** Maps one exact canonical entity to one governed platform connector and exposes only bounded check metadata and fingerprints.
8. **Live Verification Engine (`core/verification/`):** Collects live read-only telemetry only after separate activation and normalizes attributable evidence.
9. **Knowledge Lifecycle Engine (`core/lifecycle/`):** Detects knowledge drift, manages review queue, tracks freshness; **NEVER automatically overwrites canonical facts**.
10. **Execution Engine (`core/execution/`):** Remains disabled by default and accepts only explicit `MNE-BRAIN-OWNER` instructions; audit stays in memory unless the owner explicitly requests persistence.
11. **Tool Engine Drivers (`core/tools/drivers/`):** Low-level protocol drivers (SSH, REST, PowerShell, WinRM, VMware, SQL, SNMP) with zero orchestration logic.
12. **Structured Evidence-Based Answer:** Returns an evidence-status answer with source attribution and explicit unknowns.

### Offline incident boundary

- Target-dependent investigations require exactly one canonical entity.
- `related_entities` is documented adjacency only and never proves dependency health or causality.
- P3 may accept fresh P2 evidence only through the owner-authorized provenance envelope. It must not invoke transport, call an external AI provider, persist traces, promote knowledge, or execute remediation.
- Offline P4 must label impact as reported, keep priority provisional, send no notifications, create no SLA, and persist no case or timeline.
- P5 must exclude runbook bodies, report procedure coverage separately from live-state truth, and require an explicit sole-owner instruction for promotion. The owner may authorize one runbook or an entire named phase; no ticket, second approval, or approval reference is required.
- P6 must map every entity exactly once, expose fingerprints instead of raw operations, treat fixture output as trust 0, and keep all live transports disabled until an exact target/check scope, registered adapter, and opaque credential reference satisfy the sole-owner gate.
- P7 must use schema-governed local environment bindings, pinned SSH/TLS or Kerberos identity, one allowlisted read-only check per scope, and in-memory-only evidence. Owner-excluded bindings are skipped without retries; live policy remains disabled at rest.
- P8 must require one exact registered scenario and active operational binding, plan no more than three read-only checks, accept only fresh attributable trust-5 evidence, and keep AI handoffs below 6,000 characters. Operational reconciliation never promotes canonical facts automatically; live collection, persistence, external AI, notifications, ticketing, paging, assignment, and remediation remain disabled at rest.
- P9 must execute only immutable schema-governed read-only operations for one exact scenario, use no more than three bindings and four checks per session, discard raw output after normalization, and require every AI conclusion to cite accepted fresh trust-5 evidence. Python may rank checks and validate assessments but must not encode root-cause reasoning. Stop early requires at least 95% evidence-bound confidence.

---

## 3. Controlled Autonomous Remediation Framework

### Supreme Write Safety Rule
> **Forbidden by Default:** Read-Only discovery remains the permanent default mode. The AI Agent may perform write operations ONLY through the Controlled Autonomous Remediation Engine (`actions/`, `config/action_policy.yaml`, `tasks/remediate.md`). Unrestricted write access is strictly prohibited.

### 5-Level Risk Classification Model

| Level | Action Type | Examples | Policy |
| :--- | :--- | :--- | :--- |
| **Level 0** | **Read Only** | `show` commands, API GETs, telemetry discovery | **May run only after `MNE-BRAIN-OWNER` explicitly says `proceed`, with exact scope and policy activation** |
| **Level 1** | **Low Risk** | Clear interface counters, refresh status, re-run health checks | **Explicit sole-owner instruction** |
| **Level 2** | **Controlled Change** | Modify address object, add VLAN description, toggle F5 pool member | **Explicit sole-owner instruction** |
| **Level 3** | **High Impact** | Firewall policy changes, routing changes, service restarts | **Explicit sole-owner instruction** |
| **Level 4** | **Emergency Only** | Core firewall changes, SAN LUN modifications, Exchange DAG changes | **STRICTLY PROHIBITED** |

---

## 4. Credential Architecture & Secret Protection Policy

- Plaintext passwords, API tokens, SNMP strings, SSH keys, and certificates MUST NEVER exist in tracked files, Markdown documentation, YAML profiles, or code.
- Credential values may be stored in local `.env` or other ignored local credential files. Tracked code and profiles may contain only environment-variable reference names.
- Profiles and discovery contracts contain zero credential values and resolve targets only through canonical entity IDs.
- Telemetry outputs filter out secrets automatically before context building.

---

## 5. Architectural GUI Rule: Presentation-Only

> **Mandatory Rule:** The GUI must NEVER contain business logic. The GUI is 100% responsible for presentation (rendering topology maps, query responses, and investigation state). All reasoning, policy evaluation, live verification, and decision-making remain strictly inside `MNE_Brain`.

---

## 6. Schema-First Contract Governance

Every entity, profile, task, evidence pack, and action template in Release 2 must strictly conform to its JSON Schema in `00_meta/schemas/`:
- `profile.schema.json`
- `task.schema.json`
- `evidence.schema.json`
- `action.schema.json`
- `p8-diagnostic-catalog.schema.json`
- `p9-diagnostic-catalog.schema.json`
- `entity.schema.json`
