# Controlled Autonomous Remediation Framework

> **Supreme Security Rule:** Read-Only mode is active by default. Write operations are forbidden by default. The AI Agent may perform write operations ONLY through approved, auditable, and policy-validated Action Templates.

---

## 📁 Directory Architecture

```
actions/
├── README.md               # Framework Architecture & Security Policies
├── templates/             # Approved Remediation Action Templates
├── approved/              # Policy-Authorized Active Actions (Staged)
└── pending/               # Actions Awaiting Human Operator Approval
```

---

## 🛡️ Risk Classification Model (Level 0 – Level 4)

| Risk Level | Impact Category | Action Examples | Approval Policy |
| :--- | :--- | :--- | :--- |
| **Level 0** | **Read Only** | `show` commands, API GETs, telemetry discovery | **Always Allowed** (No infrastructure impact) |
| **Level 1** | **Low Risk** | Clear interface counters, refresh status, re-run health checks | **Autonomous** if policy allows |
| **Level 2** | **Controlled Change** | Modify address object, add VLAN description, toggle F5 pool member | **Requires Policy Approval** (`config/action_policy.yaml`) |
| **Level 3** | **High Impact** | Firewall policy changes, routing changes, service restarts | **Human Approval Required** |
| **Level 4** | **Emergency Only** | Core firewall changes, SAN LUN modifications, Exchange DAG changes | **STRICTLY PROHIBITED** from autonomous execution |

---

## 🔄 Mandatory Remediation Workflow

```
Incident ──> Evidence Collection ──> Root Cause Verification ──> Action Selection ──> Risk Assessment ──> Approval Check ──> Pre-Check & Backup ──> Execute Action ──> Post-Validation ──> Update Vault ──> Audit Report
```
