# Action: FortiGate — Add Address Object

- **Action Name:** `fortigate_add_address_object`
- **Target Platform:** FortiGate Firewalls (FortiOS)
- **Risk Level:** Level 2 (Controlled Change)
- **Required Approval:** Requires Operator Approval
- **Status:** REQUIRES APPROVAL

## 1. Purpose
Create a new named IPv4 address object in FortiGate VDOM `root` for policy assignment.

## 2. When Allowed & Forbidden
- **When Allowed:** Target IP is verified as a valid network endpoint requiring policy rule inclusion.
- **When Forbidden:** Subnet masks overlap with existing objects; target IP is unverified.

## 3. Required Evidence
- Verification report in `operations/discovery/` proving endpoint IP allocation.

## 4. Pre-Checks
```bash
config firewall address
show | grep <OBJECT_NAME>
```

## 5. Execution Commands
```bash
config firewall address
    edit "<OBJECT_NAME>"
        set subnet <IP_ADDRESS> 255.255.255.255
        set comment "Added via Controlled Remediation"
    next
end
```

## 6. Rollback Procedure
```bash
config firewall address
    delete "<OBJECT_NAME>"
end
```

## 7. Post-Validation
```bash
get firewall address <OBJECT_NAME>
```
