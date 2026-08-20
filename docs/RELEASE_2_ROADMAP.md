# MNE_Brain Release 2 — Final Master Milestone Roadmap

> **Platform Version:** Release 2 (v2.0.0-MNE)  
> **Project Scope:** `MNE_Brain_v2` (Focused exclusively on MNE_Brain)  
> **Core Philosophy:** A Senior Infrastructure Engineer Implemented in Software  
> **Status:** OWNER-CONTROLLED ROADMAP  

---

## 🗺️ Master 14-Milestone Sequence

```
Milestone 0: Release 1 Freeze & Baseline (MNE_Brain_v1)
     ↓
Milestone 1: Architecture Contracts & Governance (AGENTS.md, ADRs, Schemas)
     ↓
Milestone 2: Core Flow Engine (Query Router, Entity Resolver, Evidence Pack)
     ↓
Milestone 3: Reasoning Engine (Investigation Planner, Information Gain, Stop Early)
     ↓
Milestone 4: Policy Engine (Safety Gates, Read-Only Policy, Sole-Owner Instructions)
     ↓
Milestone 5: Live Verification Engine (Adapters, Normalization, Trust Attribution)
     ↓
Milestone 6: Knowledge Lifecycle Engine (Drift Detection, Review Queue, Canonical Promotion)
     ↓
Milestone 7: LLM Adapter & Provider Abstraction Layer (Hot-swappable Backends)
     ↓
Milestone 8: Execution Engine (Retry, Audit Logs, Timeout, Rollback Orchestration)
     ↓
Milestone 9: Tool Engine Drivers (SSH, REST, PowerShell, WinRM, VMware, SQL, SNMP)
     ↓
Milestone 10: n8n Workflow Automation Integration (Alert Webhooks)
     ↓
Milestone 11: Controlled Remediation Planning Engine (Safety Actions)
     ↓
Milestone 12: GUI & Presentation Dashboard (Zero Business Logic Rule)
     ↓
Milestone 13: Validation, Benchmarks & End-to-End MNE_Brain Verification
```

---

## 📌 Detailed Milestone Specifications & Acceptance Criteria

### 🚩 Milestone 0: Release 1 Freeze & Baseline
* **Objective:** Freeze `MNE_Brain_v1` as the permanent reference implementation.
* **Acceptance Criteria:** `python d:/projects/MNE_Brain_v1/scripts/validate_brain.py` passes 100% of checks (11 benchmarks & 12 quality gates).

---

### 🚩 Milestone 1: Architecture Contracts & Governance
* **Objective:** Establish governance, naming conventions, contracts, schemas, and Architecture Decision Records (ADRs) before core code is written.
* **Deliverables:** `AGENTS.md` review, naming conventions spec, JSON Schemas (`00_meta/schemas/`), ADRs (`00_meta/adr/`).
* **Acceptance Criteria:** All contracts, schemas, and ADRs published and validated in `00_meta/`.

---

### 🚩 Milestone 2: Core Flow Engine
* **Objective:** Build the deterministic query routing, entity resolution, and evidence pack context engine.
* **Deliverables:** `core/router/route_query.py`, `core/entity/build_entity_index.py`, `core/evidence/build_evidence_pack.py`.
* **Acceptance Criteria:** Evidence pack context strictly bounded **<1,500 tokens** per query with 100% source attribution.

---

### 🚩 Milestone 3: Reasoning Engine
* **Objective:** Implement the stateful diagnostic reasoning engine.
* **Deliverables:** Investigation Planner, Information Gain ($H$) calculation, Stop Early Principle, Confidence Engine.
* **Acceptance Criteria:** Simulated outage benchmark (`benchmarks/simulated_outage.yaml`) completes diagnosis in minimal telemetry steps.

---

### 🚩 Milestone 4: Policy Engine
* **Objective:** Implement a lightweight, deterministic Policy Engine between reasoning and execution.
* **Deliverables:** Verification necessity rules, read-only policy enforcer, sole-owner instruction evaluator (Level 0–4 risk per `config/action_policy.yaml`), operational constraints.
* **Acceptance Criteria:** Policy Engine successfully evaluates Level 0–4 risk decisions without embedding reasoning logic.

---

### 🚩 Milestone 5: Live Verification Engine
* **Objective:** Build read-only CLI/API verification adapters for live device telemetry collection.
* **Deliverables:** Generic verification engine, schema-governed P6 connector catalog, injected adapter boundary, data normalization, and 5-tier trust attribution.
* **Current acceptance:** 15 connector families provide exact offline plans and trust-0 fixture validation for 46/46 entities. Only the FortiGate edge transport has completed an owner-gated live read; all live policies remain disabled.
* **Final live acceptance:** Each remaining platform requires a separate exact owner-controlled transport validation before it may return trust-level-5 evidence.

---

### 🚩 Milestone 6: Knowledge Lifecycle Engine
* **Objective:** Manage the evolution and freshness of the Knowledge Base following Live Verification.
* **Deliverables:** Knowledge drift detection, suggested knowledge updates, review queue, canonical knowledge promotion model, verification history & freshness tracking.
* **Acceptance Criteria:** Drift detection identifies discrepancies; zero automatic overwrites of canonical knowledge permitted.

---

### 🚩 Milestone 7: LLM Adapter & Provider Abstraction Layer
* **Objective:** Implement a vendor-neutral LLM provider layer.
* **Deliverables:** Provider interface (`core/llm/`) supporting OpenAI, Anthropic, Google Gemini, Ollama, DeepSeek.
* **Acceptance Criteria:** MNE_Brain core flow executes identically across 3 distinct LLM backends.

---

### 🚩 Milestone 8: Execution Engine
* **Objective:** Build the action execution engine responsible for retry policy, timeout handling, parallel execution, cancellation, audit logging, progress tracking, and rollback orchestration.
* **Deliverables:** `core/execution/execution_engine.py`, audit logger, rollback orchestrator.
* **Acceptance Criteria:** Execution engine orchestrates task execution and rollback cleanly upon simulated failure.

---

### 🚩 Milestone 9: Tool Engine Drivers
* **Objective:** Implement simple protocol drivers containing zero orchestration logic.
* **Deliverables:** SSH Driver, REST Driver, PowerShell Driver, WinRM Driver, VMware Driver, SQL Driver, SNMP Driver (`core/tools/drivers/`).
* **Acceptance Criteria:** Protocol drivers execute commands cleanly without embedded orchestration logic.

---

### 🚩 Milestone 10: n8n Workflow Automation Integration
* **Objective:** Preserve an optional webhook boundary without enabling automatic investigation, notification, ticketing, paging, assignment, or remediation.
* **Deliverables:** A fail-closed webhook listener contract with ingestion disabled by policy.
* **Acceptance Criteria:** Incoming webhook alerts remain blocked and trigger no automatic action.

---

### 🚩 Milestone 11: Controlled Remediation Planning Engine
* **Objective:** Implement fail-closed safety gates and redacted plans without enabling write execution.
* **Deliverables:** Pre-remediation 6-question criteria enforcement (`tasks/remediate.md`), governed action-template metadata, rollback-plan verification, explicit sole-owner instruction, and a non-executing API boundary.
* **Acceptance Criteria:** Level 4 (Emergency Core Change) is hard-blocked; Level 2 requires evidence, policy, and explicit `MNE-BRAIN-OWNER` instruction before planning readiness; no remediation driver can be invoked.

---

### 🚩 Milestone 12: GUI & Presentation Dashboard
* **Objective:** Build a truthful, read-only presentation console for backend evidence and capability states.
* **Architectural Constraint:** **ZERO Business Logic in GUI.** Presentation ONLY.
* **Deliverables:** Responsive evidence console for query responses, entity and knowledge status, investigation traces, redacted remediation metadata, alert-ingestion state, and audit records.
* **Acceptance Criteria:** The GUI renders explicit backend states with zero embedded decision logic, no mutation or credential controls, no simulated operational claims, safe dynamic text handling, and static-file containment.

---

### 🚩 Milestone 13: Validation, Benchmarks & End-to-End MNE_Brain Verification
* **Objective:** Execute a deterministic offline quality gate and Ministry-domain evidence-flow benchmarks without implying operational readiness.
* **Deliverables:** 15-step non-executing validation suite (`scripts/validate_brain.py`), 11 infrastructure evidence-flow scenarios, isolated failure and recovery fixtures, and bounded scalability checks.
* **Acceptance Criteria:** All 15 gates and 11 scenarios pass; unsupported cases remain `INSUFFICIENT_EVIDENCE`; validation performs no network, command, remediation, or project-state mutation; performance budgets are recorded separately from safety results.
