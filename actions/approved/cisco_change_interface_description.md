# Action: Cisco — Update Interface Description

- **Action Name:** `cisco_change_interface_description`
- **Target Platform:** Cisco Catalyst Switches (IOS-XE)
- **Risk Level:** Level 1 (Low Risk)
- **Required Approval:** Operator Approval
- **Status:** REQUIRES APPROVAL

## 1. Purpose
Update switch port description to reflect newly discovered endpoint connectivity.

## 2. Pre-Checks
```bash
show interface <INTERFACE_ID> description
```

## 3. Execution Commands
```bash
configure terminal
interface <INTERFACE_ID>
 description <NEW_DESCRIPTION>
end
```

## 4. Rollback Procedure
```bash
configure terminal
interface <INTERFACE_ID>
 description <OLD_DESCRIPTION>
end
```

## 5. Post-Validation
```bash
show interface <INTERFACE_ID> description
```
