# Brain Architecture Simplification Review — 2026

**Role:** Chief Brain Architect  
**Objective:** Reduce repository complexity, eliminate code bloat, and convert custom software framework abstractions into AI-Native Brain assets while preserving 100% of capabilities.

---

## 🏛️ Core Architectural Philosophy Shift

```
BEFORE (Software Framework Model):
Task ──> Large Python Orchestrator ──> Python Connectors ──> JSON Configs ──> Infrastructure

AFTER (AI-Native Brain Model):
Task (tasks/*.md) ──> Discovery Profile (profiles/*.yaml) ──> AI Agent ──> Infrastructure
```

- **Knowledge Over Code:** Replaced custom Python connector classes with declarative **AI-Native Discovery Profiles** (`profiles/*.yaml`).
- **Markdown & YAML Over Python & JSON:** Converted JSON configurations to clean YAML and Markdown profiles readable by any AI model.
- **AI Agent as Orchestrator:** Removed heavy orchestrator abstractions in favor of AI-native task execution.

---

## 📋 Summary of Architectural Changes

### 1. Deleted Unnecessary Components
- **`connectors/` directory:** Deleted all 13 custom Python connector files (`fortigate.py`, `cisco.py`, `fmc.py`, `ftd.py`, `f5.py`, `vmware.py`, `exchange.py`, `ad.py`, `dns.py`, `dhcp.py`, `sccm.py`, `linux.py`, `san.py`).
- **`config/discovery_config.json`:** Replaced heavy JSON config with declarative `config/discovery_config.yaml`.

### 2. Converted Code into Knowledge Assets (`profiles/`)
Created 8 declarative YAML Discovery Profiles under `profiles/`:
1. `profiles/fortigate.yaml`
2. `profiles/cisco.yaml`
3. `profiles/f5.yaml`
4. `profiles/vmware.yaml`
5. `profiles/exchange.yaml`
6. `profiles/identity.yaml`
7. `profiles/linux.yaml`
8. `profiles/storage.yaml`

Each profile explicitly defines: Purpose, Platform, Trust Level, Connection Parameters, Read Commands, Normalization Targets, and Update Policies.

### 3. Preserved 100% of System Capabilities
- All 6 Discovery Tasks (`network`, `virtualization`, `identity`, `messaging`, `linux`, `storage`).
- All 6 Scheduled GitHub Actions workflows on `runs-on: self-hosted`.
- Two-Stage Knowledge Update & 5-tier Trust Level Model.
- Investigation Planning, Information Gain, Evidence Ranking, and Observation-Interpretation Framework.
- Vendor-neutral compatibility with Antigravity, Codex, Claude, OpenCode, and Pi.
