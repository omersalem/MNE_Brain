# Action Template: Generic Remediation Procedure

- **Action Name:** Generic Remediation
- **Target Platform:** Generic
- **Risk Level:** Level 2 (Controlled Change)
- **Required Approval:** Requires Operator Approval
- **Status:** REQUIRES APPROVAL

## 1. Purpose
Describe the exact operational purpose of this remediation action.

## 2. When Allowed & Forbidden
- **When Allowed:** Problem is VERIFIED with hard telemetry evidence; root cause is isolated.
- **When Forbidden:** Evidence is missing (`MEDIUM`/`LOW` confidence); no rollback plan defined.

## 3. Required Evidence
- Hard evidence log or telemetry proving root cause.

## 4. Affected Systems
- List target hostnames, IP addresses, and interfaces.

## 5. Pre-Checks
- Commands to verify pre-remediation baseline.

## 6. Execution Commands
```bash
# Approved Write Commands
```

## 7. Expected Result
- Expected post-remediation system state.

## 8. Rollback Procedure
```bash
# Rollback Commands
```

## 9. Post-Validation
- Commands to verify operational success.

## 10. Audit Information
- Logged to `operations/actions/YYYY-MM-DD-action-name.md`.
