# MNE_Brain Release 2 — Architecture Specification

> **Platform Version:** Release 2 (v2.0.0-MNE)  
> **Project Scope:** `MNE_Brain_v2` (Focused strictly on MNE_Brain Infrastructure Brain)  
> **Core Philosophy:** A Senior Infrastructure Engineer Implemented in Software  
> **Author:** Chief Software Architect & AI Systems Architect  
> **Status:** Architecture blueprint with P2 offline implementation; live and production operation remain disabled pending explicit sole-owner instruction  

---

## 🏛️ System Architecture Overview

**MNE_Brain Release 2** is architected as a schema-first, token-optimized, policy-governed AI-native infrastructure brain for multi-domain enterprise troubleshooting. The current repository supports exact-target offline incident orchestration, evidence-bounded diagnosis, and an injected-transport read-only contract. It does not yet operate against live Ministry infrastructure.

```mermaid
graph TD
    UserQuery[User Question / Alert Webhook] --> CoreFlow["1. Core Flow (Query Router -> Entity Resolution -> Evidence Pack)"]
    
    CoreFlow -->|Token-Bounded Context (<1,500 tokens)| ReasoningEngine["2. Reasoning Engine (Investigation Planner -> Info Gain -> Stop Early)"]
    
    ReasoningEngine -->|Proposed Action / Telemetry Request| PolicyEngine["3. Policy Engine (Read-Only Policy -> Risk Gates)"]
    
    PolicyEngine -->|Verification Needed| LiveVerify["4. Live Verification Engine (Telemetry Capture -> Trust Attribution)"]
    LiveVerify -->|Raw Telemetry| PhysicalInfra["Target Infrastructure Devices"]
    PhysicalInfra --> LiveVerify
    
    LiveVerify --> KnowledgeLifecycle["5. Knowledge Lifecycle Engine (Drift Detection -> Review Queue)"]
    
    KnowledgeLifecycle -->|Execution Needed| ExecutionEngine["6. Execution Engine (Retry -> Audit -> Rollback)"]
    ExecutionEngine --> ToolDrivers["7. Tool Engine Drivers (SSH, REST, PowerShell, WinRM, VMware, SQL, SNMP)"]
    ToolDrivers --> PhysicalInfra
    
    KnowledgeLifecycle -->|Conclusion Reached| AnswerGen["8. Structured Evidence-Based Answer"]
    AnswerGen --> GUI["9. Presentation GUI (ZERO Business Logic)"]
```

---

## 🧠 Core Component Specifications

### 1. Architecture Contracts (`00_meta/`)
Governs repository rules, naming conventions, JSON/YAML Schemas (`00_meta/schemas/`), and Architecture Decision Records (`00_meta/adr/`). Establishes governance before code implementation.

### 2. Core Flow Engine (`core/router/`, `core/entity/`, `core/evidence/`)
* **Query Router:** Deterministic AST parser classifying query intent without LLM token cost.
* **Entity Resolver:** Resolves hostnames, FQDNs, IP addresses, and serial numbers against cached index (`00_meta/indices/entity-index.json`).
* **Evidence Pack Engine:** Extracts token-bounded context blocks (**<1,500 tokens**) with strict 5-tier trust attribution tags. Replaces traditional RAG.

### 3. Reasoning Engine (`core/reasoning/`)
Executes an iterative diagnostic state graph. Calculates Information Gain ($H$) at each step and enforces the **Stop Early Principle** (terminating telemetry calls as soon as root cause certainty >95%).

### 3A. Incident Orchestration (`core/orchestration/`)
P3 assembles target resolution, documented adjacency, evidence validation, reasoning state, policy outcome, ordered evidence objectives, metrics, and a compact AI handoff. It requires an exact canonical target for operational questions and treats every relationship as context rather than current health or causality. P3 never opens a live connection; policy permits only fresh, allowlisted P2 records through a validated in-memory envelope and still prohibits external AI calls, persistence, lifecycle promotion, and remediation.

### 3B. Incident Case Management (`core/incidents/`)
P4 wraps the investigation with schema-bounded owner-reported impact, provisional priority, sole-owner control, continuation, reported objective outcomes, a bounded timeline, and a minimized handoff packet. Reported impact is never promoted to verified truth, priority requires owner confirmation, and no SLA, notification, ticket, automatic assignment/remediation, or persistent case is created.

### 3C. Runbook Intelligence (`core/runbooks/`)
P5 validates and ranks governed troubleshooting runbook metadata using exact entity, service, and controlled category matching. It returns at most three candidates and never injects runbook bodies. Context coverage, sole-owner-reviewed procedure coverage, live-state truth, and production readiness are separate claims. Promotion is never automatic and requires an explicit instruction from `MNE-BRAIN-OWNER`; the owner may authorize a whole named phase without a ticket or second approval.

### 3D. Connector Intelligence (`core/connectors/`)
P6 maps each canonical entity to exactly one schema-governed platform connector. The registry returns check IDs, evidence objectives, and operation fingerprints without raw operations, addresses, or credentials. Fifteen families cover all 46 entities; every route passes an injected trust-0 fixture, while live collection remains disabled. The connector layer contains no diagnosis or remediation logic and reuses the P2 evidence adapter for redaction, budgets, provenance, and trust.

### 4. Policy Engine (`core/policy/`)
A lightweight, deterministic policy layer positioned between Reasoning and Execution:
* **Verification Necessity:** Evaluates whether live verification is required or cached Level 3 knowledge is sufficient.
* **Read-Only Enforcement:** Ensures read-only telemetry satisfies query constraints.
* **Sole-Owner Action Policy:** Evaluates Level 0–4 risk levels and requires explicit `MNE-BRAIN-OWNER` instruction for changes.
* **Operational Constraints:** Enforces blackout windows, rate limits, and safety boundaries.
* *Note:* The Policy Engine is a deterministic governance layer, NOT an LLM reasoning engine.

### 5. Live Verification Engine (`core/verification/`)
The P2 core defines a transport-neutral, injected read-only adapter contract and normalizes successful attributable results into 5-tier evidence. The explicit FortiGate integration uses PuTTY Plink with an exact target, pinned host key, temporary password file, exact command allowlist, timeout, and minimized failure states. Live policy is disabled except when `MNE-BRAIN-OWNER` explicitly says `proceed`; simulation can produce only trust-0 evidence. Live collection requires the registered adapter, P0 reference, fixed owner reference, explicit owner proceed state, exact entity scope, and bounded check allowlist.

### 6. Knowledge Lifecycle Engine (`core/lifecycle/`)
Manages the evolution of the Knowledge Base after Live Verification:
* **Knowledge Drift Detection:** Identifies discrepancies between live telemetry and canonical facts.
* **Suggested Knowledge Updates & Review Queue:** Stages proposed note updates for sole-owner review only when persistence is explicitly requested.
* **Canonical Promotion & Verification History:** Tracks last verified timestamps, freshness, and version history.
* **Mandatory Constraint:** NEVER automatically overwrites canonical knowledge. Every update is traceable and evidence-backed.

### 7. Execution Engine vs. Tool Engine Drivers
Decouples action execution from protocol drivers:
* **Execution Engine (`core/execution/`):** Disabled by default; requires the fixed owner plus explicit instruction, keeps audit in memory by default, bounds retries/timeouts, and never runs rollback automatically.
* **Tool Engine Drivers (`core/tools/drivers/`):** Simple protocol drivers containing **zero orchestration logic** (SSH Driver, REST Driver, PowerShell Driver, WinRM Driver, VMware Driver, SQL Driver, SNMP Driver).

### 8. Presentation GUI Rule (`gui/`)
> **Mandatory Architectural Constraint:** The GUI must NEVER contain business logic. The GUI is 100% responsible for presentation (rendering telemetry graphs, query responses, and investigation state). All reasoning, investigation, policy evaluation, live verification, and decision-making remain strictly inside `MNE_Brain`.

---

## 📂 3-Layer Decoupled Repository Architecture

```
MNE_Brain_v2/
├── docs/                       # Release architecture documentation package
├── 00_meta/                    # Governance contracts, schemas & ADRs
│   ├── schemas/                # JSON/YAML Schemas (profile, task, evidence, action)
│   ├── adr/                    # Architecture Decision Records
│   └── indices/                # Entity index lookup tables
├── core/                       # MNE_Brain Core Engine
│   ├── router/                 # Query router service
│   ├── entity/                 # Entity resolver service
│   ├── evidence/               # Evidence pack engine
│   ├── reasoning/              # Stateful investigation reasoning engine
│   ├── policy/                 # Deterministic policy engine
│   ├── verification/           # Live telemetry verification engine
│   ├── lifecycle/              # Knowledge lifecycle engine (drift, review queue, promotion)
│   ├── llm/                    # Vendor-neutral LLM adapter provider layer
│   ├── execution/              # Action execution engine (retry, audit, rollback)
│   ├── tools/drivers/          # Protocol drivers (SSH, REST, PowerShell, WinRM, VMware, SQL, SNMP)
│   └── remediation/            # Controlled remediation policy gate
├── knowledge/                  # LAYER 1: Canonical Infrastructure Facts
├── operations/                 # LAYER 2: Transient Telemetry & History
├── intelligence/               # LAYER 3: Reusable Engineering Experience
├── profiles/                   # Declarative device discovery profiles
├── tasks/                      # AI task specifications
├── actions/                    # Controlled remediation action templates
├── gui/                        # Presentation-Only Web Dashboard (ZERO Business Logic)
└── scripts/                    # Automation CLI scripts & quality gates
```

---

## 🛡️ Zero-Trust Security & Credential Isolation

* Passwords, API tokens, and SSH keys may be stored in ignored local `.env` or credential files; tracked content contains only environment-variable references.
* Zero credentials exist in tracked code, profiles, or markdown notes.
* Redaction engine automatically filters credentials from telemetry outputs.
* Host targets come from canonical entity records; arbitrary user-supplied endpoints are not accepted by the P2 path.
