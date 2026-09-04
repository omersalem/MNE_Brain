---
name: windows-exchange-server
description: >
  Expert-level guide for managing Exchange Server 2019 on Windows Server 2019
  via Exchange Management Shell (EMS/PowerShell) AND Exchange Admin Center (EAC) GUI.
  Use this skill for ANY task involving: mailboxes, mail flow, queues, transport rules,
  connectors, databases, OWA, ActiveSync, distribution groups, shared mailboxes,
  message tracking, anti-spam, certificates, DAG, or any Exchange PowerShell cmdlet.
  Always consult this skill before answering any Exchange Server question.
---

# Exchange Server 2019
## Windows Server 2019 Standard — Expert Reference

---

## CRITICAL CONTEXT

- **Exchange Management Shell (EMS):**
  Start → Microsoft Exchange Server 2019 → Exchange Management Shell
- **Remote PowerShell session:**
  ```powershell
  $Session = New-PSSession -ConfigurationName Microsoft.Exchange `
    -ConnectionUri "http://EXCHANGE-SRV/PowerShell/" `
    -Authentication Kerberos
  Import-PSSession $Session -DisableNameChecking
  ```
- **EAC Web GUI URL:** `https://EXCHANGE-SRV/ecp`
- **OWA URL:** `https://EXCHANGE-SRV/owa`
- **ActiveSync URL:** `https://EXCHANGE-SRV/Microsoft-Server-ActiveSync`
- **Default result limit:** 1000 — always use `-ResultSize Unlimited`
- **All GUI actions run PowerShell behind the scenes**

---

## Reference Files — Load When Needed

| Topic | File | Load When |
|---|---|---|
| Mailboxes | `references/mailboxes.md` | Mailbox create/edit/quota/permissions/shared |
| Mail Flow & Queues | `references/mail-flow.md` | Queues, transport rules, connectors, tracking |
| Databases & DAG | `references/databases.md` | DB management, mounting, DAG replication |
| EAC GUI | `references/eac-gui.md` | Full EAC navigation and GUI procedures |
| Anti-Spam & Security | `references/antispam-security.md` | Spam filter, malware filter, connectors, certs |
| Troubleshooting | `references/troubleshooting.md` | Common problems, diagnostics, quick fixes |

**Always read the relevant reference file before answering.**

---

## CLI Fundamentals (Always Available)

```powershell
# Check all Exchange services
Get-Service | Where {$_.DisplayName -like "*Exchange*"} |
  Select DisplayName,Status | Sort DisplayName

# Quick health check
Test-ServiceHealth
Get-Queue | Where {$_.MessageCount -gt 0}
Get-MailboxDatabase -Status | Select Name,Mounted,DatabaseSize

# Key read commands
Get-Mailbox -ResultSize Unlimited
Get-MailboxStatistics -Identity "user"
Get-Queue
Get-MessageTrackingLog -Start (Get-Date).AddHours(-1)
```

---

## Default Access Information

```
EAC GUI:   https://EXCHANGE-SRV/ecp
OWA:       https://EXCHANGE-SRV/owa
EMS:       Start → Exchange Management Shell (run as admin)
Admin:     DOMAIN\Administrator or Exchange Admin role
```
