# Action: FortiGate — Modify Firewall Policy Rule

- **Action Name:** `fortigate_modify_policy`
- **Target Platform:** FortiGate Firewalls (FortiOS)
- **Risk Level:** Level 3 (High Impact)
- **Required Approval:** Human Operator Approval Mandatory
- **Status:** REQUIRES APPROVAL

## 1. Purpose
Add an approved address object to an existing firewall policy rule.

## 2. When Allowed & Forbidden
- **When Allowed:** Explicit ticket approval; policy ID is verified.
- **When Forbidden:** Unverified policy ID; broad `0.0.0.0/0` source/destination definitions.

## 3. Pre-Checks
```bash
show firewall policy <POLICY_ID>
```

## 4. Execution Commands
```bash
config firewall policy
    edit <POLICY_ID>
        append dstaddr "<OBJECT_NAME>"
    next
end
```

## 5. Rollback Procedure
```bash
config firewall policy
    edit <POLICY_ID>
        unselect dstaddr "<OBJECT_NAME>"
    next
end
```

## 6. Post-Validation
```bash
get firewall policy <POLICY_ID>
```
