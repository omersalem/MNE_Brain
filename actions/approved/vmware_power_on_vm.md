# Action: VMware vSphere — Power On Approved VM

- **Action Name:** `vmware_power_on_vm`
- **Target Platform:** VMware vSphere / vCenter
- **Risk Level:** Level 2 (Controlled Change)
- **Required Approval:** Operator Approval
- **Status:** REQUIRES APPROVAL

## 1. Pre-Checks
```powershell
Get-VM -Name "<VM_NAME>" | Select Name, PowerState
```

## 2. Execution Commands
```powershell
Start-VM -VM "<VM_NAME>" -Confirm:$false
```

## 3. Rollback Procedure
```powershell
Stop-VM -VM "<VM_NAME>" -Kill -Confirm:$false
```

## 4. Post-Validation
```powershell
Get-VM -Name "<VM_NAME>" | Select Name, PowerState
```
