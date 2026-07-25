# Task: Controlled Autonomous Remediation Engine (`tasks/remediate.md`)

> **Supreme Guardrail:** Write operations are forbidden by default. Read-Only mode is active by default. The AI Agent must NEVER execute write actions without completing the 7-Question Decision Checklist and verifying explicit policy authorization.

---

## 📋 The 7 Mandatory Pre-Remediation Questions

Before executing ANY remediation action, The AI Agent MUST answer all 7 questions:

1. **What is the verified problem?**  
   *(Must reference hard telemetry evidence in `operations/discovery/` or `operations/incidents/`).*

2. **What evidence proves it?**  
   *(Must cite specific read-only command output or API telemetry).*

3. **Why is this action the best solution?**  
   *(Must explain why alternative non-intrusive steps are insufficient).*

4. **What are possible side effects?**  
   *(Must identify downstream dependency impact).*

5. **What is the exact rollback procedure?**  
   *(Must specify tested rollback commands).*

6. **How will success be verified post-execution?**  
   *(Must specify post-validation read commands).*

7. **What is the current confidence level?**  
   *(Must be `VERIFIED` via live telemetry; if `MEDIUM` or `LOW` ➔ **ABORT**).*

> **Rule:** If ANY of the 7 answers is missing or unverified ➔ **DO NOT EXECUTE REMEDIATION**.

---

## 🔄 Remediation Execution Pipeline

```
Incident Detection ──> Evidence Collection ──> Root Cause Verification ──> Action Selection ──> Policy Check (config/action_policy.yaml) ──> 7-Question Decision Checklist ──> Pre-Check & Snapshot ──> Execute Action ──> Post-Validation ──> Write Audit Report (operations/actions/)
```

---

## 📝 Mandatory Action Audit Report Format

Every executed action MUST write an audit log to `operations/actions/YYYY-MM-DD-action-name.md`:

```markdown
# Remediation Action Audit Report: <ACTION_NAME>

- **Execution Timestamp:** YYYY-MM-DDTHH:MM:SS
- **Operator / Agent:** AI Agent (MNE-BRAIN-RUNNER-62)
- **Target Platform / Device:** <DEVICE_ID> (<MGMT_IP>)
- **Action Template:** `actions/approved/<ACTION_NAME>.md`
- **Risk Level:** Level 1 | Level 2 | Level 3
- **Approval Status:** Authorized per `config/action_policy.yaml`

## 1. Verified Problem & Evidence
- **Problem Statement:** <STATEMENT>
- **Telemetry Evidence:** <EVIDENCE_CITATIONS>

## 2. Executed Write Commands
```bash
<COMMANDS_EXECUTED>
```

## 3. Post-Validation Results
- **Validation Status:** VERIFIED SUCCESSFUL

## 4. Rollback Information
```bash
<ROLLBACK_COMMANDS>
```
```
