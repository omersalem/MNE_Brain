# MNE_Brain Release 2 — Architectural Delta & Evolution Matrix

> **Baseline Project:** `MNE_Brain_v1` (Frozen Baseline)  
> **Target Project:** `MNE_Brain_v2` (Independent MNE_Brain Workspace)  
> **Core Philosophy:** A Senior Infrastructure Engineer Implemented in Software  
> **Author:** Chief Software Architect & Brain Architect  

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
| **LLM Provider Layer** | Hardcoded model calls. | **Vendor-Neutral LLM Adapter** | **Provider Abstraction** | Hot-swappable OpenAI, Anthropic, Gemini, Ollama, DeepSeek. |
| **Validation Gate** | 12-step validation script. | **15-Step Quality Gate & 11 Infrastructure Benchmarks** | **MNE_Brain Verification** | Tests MNE_Brain infrastructure performance directly. |

---

## 🔍 Summary of Preserved Assets

1. **3-Layer Decoupled Architecture (`knowledge/`, `operations/`, `intelligence/`).**
2. **Declarative Device Profiles (`profiles/*.yaml`).**
3. **5-Tier Trust Level Standard ($\star\star\star\star\star$ scale).**
4. **Controlled Autonomous Remediation Framework (Level 0 to Level 4).**
5. **Zero-Trust Credential Isolation Policy (`.env` local storage).**
