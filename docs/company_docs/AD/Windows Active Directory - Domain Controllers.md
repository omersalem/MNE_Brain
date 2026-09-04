# Domain Controllers & AD Health
## Windows Server 2019

---

## DOMAIN CONTROLLERS — PowerShell

### Read (Safe)

```powershell
# List all Domain Controllers
Get-ADDomainController -Filter * |
  Select Name,IPv4Address,Site,IsGlobalCatalog,IsReadOnly,OperatingSystem

# Get specific DC info
Get-ADDomainController -Identity "DC01"

# Get domain info
Get-ADDomain | Select DNSRoot,NetBIOSName,DomainMode,PDCEmulator,RIDMaster,InfrastructureMaster

# Get forest info
Get-ADForest | Select Name,ForestMode,SchemaMaster,DomainNamingMaster,Sites

# Get ALL FSMO roles at once
Write-Host "=== FSMO Roles ===" -ForegroundColor Cyan
$domain = Get-ADDomain
$forest = Get-ADForest
[PSCustomObject]@{
  PDCEmulator           = $domain.PDCEmulator
  RIDMaster             = $domain.RIDMaster
  InfrastructureMaster  = $domain.InfrastructureMaster
  SchemaMaster          = $forest.SchemaMaster
  DomainNamingMaster    = $forest.DomainNamingMaster
}

# Alternative: command line
netdom query fsmo

# Check DC services
Get-Service -ComputerName DC01 `
  -Name NTDS,Netlogon,DFSR,DNS,Kerberos,W32Time |
  Select DisplayName,Status

# Check DC time sync (critical for Kerberos)
w32tm /query /status
w32tm /query /peers
w32tm /stripchart /computer:DC01 /samples:5

# Check Netlogon service
Get-Service -Name Netlogon
Get-Content "C:\Windows\debug\netlogon.log" | Select-Object -Last 50

# Check AD DS service
Get-Service -Name NTDS

# Check sysvol/netlogon shares
net share | Select-String "SYSVOL|NETLOGON"
```

### FSMO Role Transfer (Require Confirmation)

```powershell
# Transfer PDC Emulator to DC02
Move-ADDirectoryServerOperationMasterRole -Identity "DC02" `
  -OperationMasterRole PDCEmulator

# Transfer multiple roles at once
Move-ADDirectoryServerOperationMasterRole -Identity "DC02" `
  -OperationMasterRole PDCEmulator,RIDMaster,InfrastructureMaster

# Seize role (if original DC is offline — use with caution)
Move-ADDirectoryServerOperationMasterRole -Identity "DC02" `
  -OperationMasterRole PDCEmulator -Force
```

---

## DCDIAG — Health Checks

```powershell
# Full health check (verbose)
dcdiag /v

# Run on remote DC
dcdiag /s:DC01 /v

# Run specific tests only
dcdiag /test:replications /v     # Replication health
dcdiag /test:connectivity /v     # DC connectivity
dcdiag /test:netlogons /v        # Netlogon service
dcdiag /test:advertising /v      # DC advertising in DNS
dcdiag /test:services /v         # Required services
dcdiag /test:frsevent /v         # FRS/DFSR events
dcdiag /test:systemlog /v        # System event log errors
dcdiag /test:kccevent /v         # KCC topology events

# Run ALL tests and save to file
dcdiag /v /c /f:C:\dcdiag-output.txt

# Run tests on all DCs in the domain
dcdiag /e /v
```

### Key dcdiag test interpretations:
```
PASSED — Test passed, no issues
FAILED — Issue found, read the details
WARNING — Minor issue, monitor

Common failures:
  "The server is not responding to DS RPC bind" → DC unreachable
  "LDAP bind failed" → LDAP service issue
  "Advertising fails" → DC not registered in DNS
  "MachineAccount" failure → Computer account issue
```

---

## REPADMIN — Replication Diagnostics

```powershell
# Show replication status for all DCs
repadmin /showrepl

# Show replication summary (fastest overview)
repadmin /replsummary

# Show replication status for specific DC
repadmin /showrepl DC01

# Show replication partners of a DC
repadmin /showrepl DC01 /repsto   # show inbound partners
repadmin /showrepl DC01 /repsfo   # show outbound partners

# Check for replication failures
repadmin /showrepl * /errorsonly

# Show last replication time per partition
repadmin /showutdvec DC01 dc=domain,dc=com

# View replication queue (pending)
repadmin /queue DC01

# Force immediate replication from all partners
repadmin /syncall DC01 /AdeP
# Flags: A=all partitions, d=identify partners by DN, e=enterprise-wide, P=push

# Force sync specific partition from specific partner
repadmin /replicate DC02 DC01 "dc=domain,dc=com"

# Show metadata for a specific object (who last changed it)
repadmin /showobjmeta DC01 "CN=John Smith,OU=Users,DC=domain,DC=com"

# Show bridgeheads
repadmin /bridgeheads

# Test replication topology
repadmin /checkprop
```

### Common repadmin error messages:
```
"There is no such object on the server"
  → Object was deleted but replication hasn't propagated — wait or force sync

"The replication operation encountered a database error"
  → Run: ntdsutil "activate instance ntds" "files" "integrity" quit quit

"Access is denied"
  → Check DC computer account, secure channel

"The target principal name is incorrect"
  → Kerberos/time issue — check w32tm sync
```

---

## DOMAIN CONTROLLER — GUI

### Server Manager — AD DS Dashboard
```
Server Manager → Dashboard → AD DS (left panel)
  Shows:
    - All DCs in domain
    - Service status per DC
    - Event summary (errors/warnings)
  Right-click any DC → Manage As... (connect as different user)
```

### Active Directory Users and Computers — DC Container
```
ADUC → Domain Controllers OU
  Shows all DC computer accounts
  Right-click DC → Properties →
    General tab → DC computer account info
    Operating System tab → OS version
    Dial-in → Remote access
    Member Of → Group memberships
```

### FSMO Roles — GUI

**RID Master, PDC Emulator, Infrastructure Master:**
```
ADUC → Right-click domain root → Operations Masters
  Tabs: RID | PDC | Infrastructure
  Each tab shows current holder
  "Transfer" button → transfers role to the DC you're connected to
  ⚠️ Must be connected to the TARGET DC to transfer to it
  Right-click domain root → Change Domain Controller → select DC → then transfer
```

**Domain Naming Master:**
```
Run: domain.msc (Active Directory Domains and Trusts)
  Right-click "Active Directory Domains and Trusts" root
  → Operations Master
  Shows current Domain Naming Master
  "Transfer" button to move role
```

**Schema Master:**
```
Step 1: Register schema MMC snap-in (one time only)
  Run: regsvr32 schmmgmt.dll

Step 2: Add snap-in
  Run: mmc
  File → Add/Remove Snap-in → Active Directory Schema → Add → OK

Step 3: View/transfer Schema Master
  Right-click "Active Directory Schema" → Operations Master
  "Transfer" button to move role
```

### Active Directory Sites and Services (dssite.msc)
```
dssite.msc (or Server Manager → Tools → AD Sites and Services)

Tree structure:
  Sites
  ├── Default-First-Site-Name (or your site names)
  │     ├── Servers
  │     │     └── DC01
  │     │           └── NTDS Settings
  │     │                 └── [Connection objects — replication links]
  │     └── Subnets associated with this site
  └── Inter-Site Transports
        ├── IP      ← RPC over IP (default, recommended)
        └── SMTP    ← For unreliable WAN links only

Force replication via GUI:
  Sites → [Site] → Servers → DC01 → NTDS Settings
  Right-click a connection object → Replicate Now

Check replication topology:
  Right-click NTDS Settings → All Tasks → Check Replication Topology
  (This triggers KCC to recalculate)
```
