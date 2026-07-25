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

## 3. Credential Protection & Secret Policy
- Credentials, passwords, tokens, private SSH keys, and API secrets are used internally ONLY by read/action execution paths.
- **NEVER** expose, print, or leak credentials in chat responses, artifacts, or summaries unless explicitly requested by the user.

---

## 4. Observation, Interpretation & Conclusion Framework
```
Observation (Direct Fact) ──> Interpretation (Hypothesis) ──> Required Verification (Action) ──> Conclusion (Verified Decision)
```

---

## 5. Read-Only Default Safety Rules
- Read-only discovery remains active by default.
- Never execute configuration changes without policy authorization, rollback plans, and action audit logs (`operations/actions/`).
