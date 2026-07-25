# Action: Exchange 2019 — Restart Approved Service

- **Action Name:** `exchange_restart_approved_service`
- **Target Platform:** Microsoft Exchange Server 2019
- **Risk Level:** Level 3 (High Impact)
- **Required Approval:** Human Operator Approval Mandatory
- **Status:** REQUIRES APPROVAL

## 1. Pre-Checks
```powershell
Get-Service -Name "<SERVICE_NAME>" -ComputerName "<EXCHANGE_HOST>"
```

## 2. Execution Commands
```powershell
Restart-Service -Name "<SERVICE_NAME>" -Force
```

## 3. Rollback Procedure
```powershell
Start-Service -Name "<SERVICE_NAME>"
```

## 4. Post-Validation
```powershell
Get-Service -Name "<SERVICE_NAME>" -ComputerName "<EXCHANGE_HOST>"
```
