# AGENTS.md — Supreme Repository Governance & Single Source of Truth

> **Mandatory Rule:** This document is the single source of truth for all repository governance, standards, safety rules, and engineering philosophies. All AI Agents operating on this repository behave identically and inherit 100% of their rules from this file.

---

## 1. 3-Layer Decoupled Repository Architecture
- **Layer 1 `knowledge/`:** Permanent Infrastructure Facts (Topology, Canonical Notes, Devices, Profiles).
- **Layer 2 `operations/`:** Operational History & Transient Logs (Incidents, Discovery Reports, Live Verification Outputs, Action Audits).
- **Layer 3 `intelligence/`:** Reusable Engineering Experience (SOP Runbooks, Troubleshooting Guides, Best Practices).

---

## 2. Controlled Autonomous Remediation Framework

### Supreme Write Safety Rule
> **Forbidden by Default:** Read-Only discovery remains the permanent default mode. The AI Agent may perform write operations ONLY through the Controlled Autonomous Remediation System (`actions/`, `config/action_policy.yaml`, `tasks/remediate.md`). Unrestricted write access is strictly prohibited.

### 5-Level Risk Classification Model

| Level | Action Type | Examples | Policy |
| :--- | :--- | :--- | :--- |
| **Level 0** | **Read Only** | `show` commands, API GETs, telemetry discovery | **Always Allowed** |
| **Level 1** | **Low Risk** | Clear interface counters, refresh status, re-run health checks | **Operator Approval** |
| **Level 2** | **Controlled Change** | Modify address object, add VLAN description, toggle F5 pool member | **Policy Approval Required** |
| **Level 3** | **High Impact** | Firewall policy changes, routing changes, service restarts | **Human Approval Mandatory** |
| **Level 4** | **Emergency Only** | Core firewall changes, SAN LUN modifications, Exchange DAG changes | **STRICTLY PROHIBITED** |

### Mandatory Pre-Remediation Criteria
A Write operation is permitted ONLY when:
1. The incident is **VERIFIED** via live telemetry.
2. The root cause has hard evidence.
3. The action exists in the Approved Action Library (`actions/approved/`).
4. Risk level is acceptable per `config/action_policy.yaml`.
5. Rollback procedure is defined and tested.
6. Post-validation checks are specified.
7. All 7 pre-remediation decision questions (`tasks/remediate.md`) are answered.

---

## 3. Credential Architecture & Secret Protection Policy
- Plaintext passwords, tokens, SSH keys, and certificates MUST NEVER exist in tracked files, Markdown documentation, YAML profiles, or code.
- All credentials are stored ONLY inside the local `.env` file and loaded via `python-dotenv` (`load_dotenv()` and `os.getenv()`).
- The `.env` file is never committed to Git. Only `.env.example` remains committed.
- Profiles and discovery contracts remain documentation-only and contain zero credentials or credential references.
- **NEVER** expose, print, or leak credentials in chat responses, artifacts, or summaries.


---

## 4. Observation, Interpretation & Conclusion Framework
```
Observation (Direct Fact) ──> Interpretation (Hypothesis) ──> Required Verification (Action) ──> Conclusion (Verified Decision)
```

---

## 5. Read-Only Default Safety Rules
- Read-only discovery remains active by default.
- Never execute configuration changes without policy authorization, rollback plans, and action audit logs (`operations/actions/`).

---

## 6. Refined AI Architecture & Query Flow (Version 2)
```
Question ➔ Deterministic Query Router (Phase D)
            ├── Concept / Generic Query ➔ Evidence Pack Builder (Phase C)
            └── Asset Query ➔ Entity Resolution (Phase B) ➔ Evidence Pack Builder (Phase C)
         ➔ Investigation Planning Engine (Phase D.5)
         ➔ Read-Only Verification (Phase F, if required)
         ➔ Dynamic Answer Template (Phase E)
```
- **Query Router:** `scripts/route_query.py` (Rule-based deterministic routing)
- **Entity Resolver:** `scripts/build_entity_index.py` (Modular index structure)
- **Evidence Pack Builder:** `scripts/build_evidence_pack.py` (Decoupled summary-ready context retrieval)
- **Investigation Planning Engine:** `tasks/investigate.md` (Highest information gain analysis & Stop Early principle)
- **Dynamic Templates:** `00_meta/03_ai_contracts/dynamic-answer-templates.md` (Route-tailored concise responses)
- **Credential Provider:** `config/secrets-map.yaml` & `00_meta/03_ai_contracts/credential-management.md`
- **Read-Only Verification Adapter:** `scripts/live_verify.py` & `scripts/adapters/fortigate_read.py`
- **Continuous Validation:** `scripts/validate_brain.py` (12-step quality gate)
