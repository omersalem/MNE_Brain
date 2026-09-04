---
name: windows-active-directory
description: >
  Expert-level guide for managing Active Directory Domain Services (AD DS)
  on Windows Server 2019 Standard via PowerShell AND GUI (ADUC, ADAC, GPMC).
  Use this skill for ANY task involving: AD users, groups, OUs, computers,
  domain controllers, FSMO roles, replication, GPO, locked accounts,
  password policies, AD health, dcdiag, repadmin, Get-AD* / Set-AD* /
  New-AD* / Remove-AD* cmdlets, or any ADUC / ADAC GUI navigation.
  Always consult this skill before answering any Active Directory question.
---

# Active Directory Domain Services (AD DS)
## Windows Server 2019 Standard — Expert Reference

---

## CRITICAL CONTEXT

- **Module required:** `ActiveDirectory` (RSAT)
- **Load module:** `Import-Module ActiveDirectory`
- **Install on Server:** `Install-WindowsFeature RSAT-ADDS-Tools`
- **Run As:** Domain Admin or delegated role
- **GUI Tools:**
  - `dsa.msc` — Active Directory Users and Computers (ADUC)
  - `dsac.exe` — Active Directory Administrative Center (ADAC)
  - `dssite.msc` — AD Sites and Services
  - `domain.msc` — AD Domains and Trusts
  - `gpmc.msc` — Group Policy Management Console
- **Open any tool:** Server Manager → Tools menu → select tool

---

## Reference Files — Load When Needed

| Topic | File | Load When |
|---|---|---|
| Users & Groups | `references/users-groups.md` | User management, locks, passwords, group membership |
| Computers & OUs | `references/computers-ous.md` | Computer accounts, OU structure, delegation |
| Domain Controllers | `references/domain-controllers.md` | FSMO, DC health, dcdiag, repadmin |
| Group Policy | `references/group-policy.md` | GPO create, edit, link, enforce, filter |
| Replication | `references/replication.md` | Replication topology, errors, force sync |
| Security & Audit | `references/security-audit.md` | Event IDs, audit policy, security logs |
| Troubleshooting | `references/troubleshooting.md` | Common problems, diagnostics, fixes |

**Always read the relevant reference file before answering.**

---

## CLI Fundamentals (Always Available)

```powershell
# Load module
Import-Module ActiveDirectory

# Get domain info
Get-ADDomain
Get-ADForest

# Quick health check
dcdiag /test:replications /v
repadmin /replsummary
netdom query fsmo

# Open GUI tools (from PowerShell or Run dialog)
dsa.msc          # ADUC
dsac.exe         # ADAC
gpmc.msc         # Group Policy
dssite.msc       # Sites and Services

# Key read commands (always safe)
Get-ADUser -Filter *
Get-ADGroup -Filter *
Get-ADComputer -Filter *
Get-ADDomainController -Filter *
Search-ADAccount -LockedOut
```

---

## Default Access Information

```
GUI (ADUC):   dsa.msc
GUI (ADAC):   dsac.exe
CLI:          PowerShell (as Domain Admin)
Console:      Server Manager → Tools
Domain Admin: DOMAIN\Administrator
```
