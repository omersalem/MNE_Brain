# Action: Cisco — Create Access VLAN

- **Action Name:** `cisco_create_vlan`
- **Target Platform:** Cisco Catalyst Switches (IOS-XE)
- **Risk Level:** Level 2 (Controlled Change)
- **Required Approval:** Operator Approval
- **Status:** REQUIRES APPROVAL

## 1. Pre-Checks
```bash
show vlan id <VLAN_ID>
```

## 2. Execution Commands
```bash
configure terminal
vlan <VLAN_ID>
 name <VLAN_NAME>
end
```

## 3. Rollback Procedure
```bash
configure terminal
no vlan <VLAN_ID>
end
```

## 4. Post-Validation
```bash
show vlan id <VLAN_ID>
```
