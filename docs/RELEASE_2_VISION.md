# MNE_Brain Release 2 — Strategic Vision & Architecture Philosophy

> **Platform Version:** Release 2 (v2.0.0-MNE)  
> **Project Scope:** `MNE_Brain_v2` (Independent Project Root)  
> **Core Philosophy:** A Senior Infrastructure Engineer Implemented in Software  
> **Author:** Chief Software Architect & AI Systems Architect  
> **Baseline Reference:** `MNE_Brain_v1` (Frozen Baseline)  

---

## 🎯 Strategic Vision: A Senior Infrastructure Engineer in Software

**MNE_Brain Release 2 (v2)** embodies a single clear philosophy: **A Senior Infrastructure Engineer implemented in software.**

MNE_Brain operates as an expert engineer: systematic, evidence-driven, policy-governed, cautious with production writes, disciplined about knowledge maintenance, and rigorous about verifying live state before drawing conclusions.

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

## 🧠 Fundamental Architecture Principles

### 1. Complete Knowledge Lifecycle Management
Knowledge in MNE_Brain evolves continuously via the **Knowledge Lifecycle Engine**. Following Live Verification:
* Telemetry is compared against canonical Layer 1 facts to detect **Knowledge Drift**.
* Updates are staged in a **Review Queue** with verification history and freshness metrics.
* **Mandatory Rule:** The system **NEVER automatically overwrites canonical knowledge**. All updates require human or policy verification and preserve raw evidence.

### 2. Separation of Execution Engine from Tool Drivers
Execution logic is strictly separated from protocol drivers:
* **Execution Engine (`core/execution/`):** Manages action execution, retry policies, timeouts, parallel execution, cancellation, audit logging, and rollback orchestration.
* **Tool Engine Drivers (`core/tools/drivers/`):** Protocol drivers (SSH, REST, PowerShell, WinRM, VMware, SQL, SNMP) containing **zero orchestration logic**.

### 3. Architecture Contracts First
Governance rules, naming conventions, JSON/YAML Schemas (`00_meta/schemas/`), and Architecture Decision Records (ADRs) are finalized before core code is written.

### 4. Presentation-Only GUI Rule
> **Mandatory Architectural Constraint:** The GUI must NEVER contain business logic. The GUI is 100% responsible for presentation (rendering telemetry graphs, query responses, and investigation state). All query routing, entity resolution, reasoning, policy evaluation, live verification, and decision-making remain strictly inside `MNE_Brain`.

---

## 🚫 Elimination of "RAG" Terminology

Release 2 completely replaces generic "RAG" concepts with precision AI-Native engineering terminology:

| Legacy Term | Release 2 Precision Engineering Terminology | Architectural Definition |
| :--- | :--- | :--- |
| ~~RAG / Vector RAG~~ | **Knowledge Discovery Engine** | Dynamic schema-based indexing and semantic retrieval of infrastructure facts. |
| ~~RAG Context Window~~ | **Evidence-Driven Knowledge Retrieval** | Token-bounded (<1,500 tokens) context extraction with strict source attribution. |
| ~~RAG Prompting~~ | **Knowledge-Guided Reasoning** | LLM decision-making strictly grounded in verified Level 3/4/5 evidence. |
| ~~Vector Database~~ | **Knowledge Intelligence** | Aggregation of canonical notes, SOP runbooks, and incident postmortems. |

---

## 🔒 Simplicity & Single Engineer Maintainability

* **Zero Overengineering:** Avoid complex distributed message brokers or speculative microservice abstractions.
* **Declarative Knowledge Over Code:** Standardized YAML profiles and Markdown specifications replace heavy imperative code abstractions.
* **Easy to Maintain by One Engineer:** Simple modular drivers, clear policy gates, and transparent workflow pipelines.
