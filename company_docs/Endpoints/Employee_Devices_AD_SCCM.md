# Employee Devices, Active Directory, and SCCM Integration Guide

This document details the architecture and troubleshooting procedures for employee workstation devices, Active Directory Domain Services, and System Center Configuration Manager (SCCM).

---

## Active Directory Domain Integration
- **Domain Name:** `mne.local`
- **Domain Controllers:**
  - `MNE-DC1` (`172.23.71.27`) — Primary Domain Controller
  - `MNE-DC2` (`172.23.71.28`) — Secondary Domain Controller
- **Authentication:** Kerberos/NTLMv2 for domain-joined PCs.

---

## SCCM Infrastructure
- **SCCM Server Name:** `SystemCenter`
- **SCCM IP Address:** `172.23.71.84` (VLAN 71)
- **Site Code:** `MNE`
- **Database Server:** `MNEPDB-SRV` (`172.23.71.73`) - SCCM SQL database instance.
- **Capabilities:** Tracks hardware specification, operating system builds, installed software, patch compliance, and remote management.

---

## Troubleshooting Workflows

### 1. Locked AD Accounts
- **Symptom:** User receives "Your account has been locked. Contact your administrator."
- **Resolution:**
  - Check account status via Active Directory administrative tools or PowerShell.
  - Unlock the account using Active Directory cmdlets.
  - Diagnose the cause: check for persistent stale credentials on mobile devices or expired saved network passwords.

### 2. PC Offline or Unreachable
- **Symptom:** Unable to query or connect to employee workstation.
- **Resolution:**
  - Verify IP address and MAC registration in DHCP Server (`172.23.71.32`).
  - Ping the device IP from HQ. If reachable but WMI fails, check firewall status (Windows Defender Firewall).
  - Map IP to VLAN using the Subnet Map to ensure the user is on the correct network segment.

---

## PowerShell Commands for Diagnostic Integration (For Agent Use)

The MNE Agent executes WMI queries and AD commands via PowerShell to retrieve live status.

### Active Directory Queries
```powershell
# Get user status details
Get-ADUser -Identity "username" -Properties Enabled, LockedOut, PasswordExpired, MemberOf, LastLogonDate

# Unlock AD User account (Write Mode only)
Unlock-ADAccount -Identity "username"
```

### SCCM Queries (WMI)
```powershell
# Query client hardware specification by last user logon
Get-WmiObject -Namespace "root\sms\site_MNE" -Class SMS_R_System -ComputerName "172.23.71.84" -Filter "LastLogonUserName = 'username'"

# Query software inventory for a specific resource ID
Get-WmiObject -Namespace "root\sms\site_MNE" -Class SMS_InstalledSoftware -ComputerName "172.23.71.84" -Filter "ResourceID = 16777224"
```
