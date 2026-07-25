# Troubleshooting — Exchange Server 2019
## Diagnostics, Common Problems & Quick Fixes

---

## SERVICES HEALTH CHECK

```powershell
# Check ALL Exchange services status
Get-Service | Where {$_.DisplayName -like "*Exchange*"} |
  Select DisplayName,Status,StartType |
  Sort DisplayName

# Critical services to verify are Running:
# MSExchangeADTopology     — AD topology (must be first)
# MSExchangeTransport      — Mail transport
# MSExchangeIS             — Information Store (mailbox databases)
# MSExchangeRPC            — RPC Client Access
# MSExchangeMailboxReplication — Move requests
# W3SVC                    — IIS (for OWA/EAC/ActiveSync)

# Quick test — are all required services healthy?
Test-ServiceHealth

# Check specific critical services
$services = @("MSExchangeADTopology","MSExchangeTransport","MSExchangeIS",
              "MSExchangeRPC","W3SVC","MSExchangeMailboxReplication")
Get-Service $services | Select DisplayName,Status

# Check IIS App Pools (OWA, EAC, ActiveSync)
Import-Module WebAdministration
Get-WebConfiguration system.applicationHost/applicationPools/add |
  Where {$_.name -like "*MSExchange*" -or $_.name -like "*Exchange*"} |
  Select name,state

# Check event logs for Exchange errors (last 100 errors)
Get-EventLog -LogName Application -Source *Exchange* `
  -EntryType Error -Newest 100 |
  Select TimeGenerated,Source,EventID,Message |
  Format-Table -Wrap
```

---

## PROBLEM: Mail Not Being Delivered

```powershell
# Step 1: Check queues
Get-Queue | Where {$_.MessageCount -gt 0} |
  Select Identity,Status,MessageCount,NextHopDomain,LastError

# Step 2: Look at messages in problem queue
Get-Message -Queue "EXCHANGE-SRV\Unreachable" |
  Select Subject,FromAddress,ToAddress,DateReceived,LastError | Select -First 20

# Step 3: Track the specific message
Get-MessageTrackingLog `
  -Recipients "recipient@domain.com" `
  -Start (Get-Date).AddHours(-24) `
  -ResultSize Unlimited |
  Select Timestamp,EventId,Source,Sender,MessageSubject,SourceContext

# Step 4: Check send connectors
Get-SendConnector | Select Name,Enabled,AddressSpaces,SmartHosts

# Step 5: Test mail flow
Test-MailFlow -TargetEmailAddress "jsmith@domain.com"
Test-MailFlow -TargetMailboxServer "EXCHANGE-SRV"

# Step 6: Check transport service
Get-Service MSExchangeTransport
Restart-Service MSExchangeTransport   # if stopped

# Step 7: Retry stuck queue
Get-Queue | Where {$_.Status -eq "Retry"} | Retry-Queue
```

---

## PROBLEM: OWA / EAC Not Accessible

```powershell
# Step 1: Check IIS service
Get-Service W3SVC
Get-Service WAS  # Windows Process Activation Service

# Step 2: Check IIS App Pools
Import-Module WebAdministration
Get-WebConfiguration system.applicationHost/applicationPools/add |
  Where {$_.name -like "*MSExchange*"} |
  Select name,state

# Start a stopped App Pool
Start-WebAppPool "MSExchangeOWAAppPool"
Start-WebAppPool "MSExchangeECPAppPool"

# Step 3: Reset IIS (last resort — causes brief outage)
iisreset /noforce

# Step 4: Test OWA connectivity
Test-OwaConnectivity -MailboxCredential (Get-Credential) `
  -TrustAnySSLCertificate

# Step 5: Check Exchange virtual directories
Get-OwaVirtualDirectory | Select InternalUrl,ExternalUrl
Get-EcpVirtualDirectory | Select InternalUrl,ExternalUrl
Get-ActiveSyncVirtualDirectory | Select InternalUrl,ExternalUrl
Get-WebServicesVirtualDirectory | Select InternalUrl,ExternalUrl

# Step 6: Check SSL certificate
Get-ExchangeCertificate | Select Thumbprint,Status,Services,Subject,NotAfter
```

---

## PROBLEM: Mailbox Database Dismounted

```powershell
# Step 1: Check database status
Get-MailboxDatabase -Status | Select Name,Mounted,Server,DatabaseSize

# Step 2: Mount dismounted database
Mount-Database -Identity "Mailbox Database 0001"

# If mount fails, check:
# Step 3: View database event logs
Get-EventLog -LogName Application -Source *MSExchangeIS* `
  -EntryType Error -Newest 20 |
  Select TimeGenerated,EventID,Message

# Step 4: Check database file integrity
# First, get database path
Get-MailboxDatabase -Identity "Mailbox Database 0001" | Select EdbFilePath,LogFolderPath

# Check with ESEUTIL
# From Exchange bin folder:
# eseutil /mh "C:\ExchangeDatabases\MBX01\MBX01.edb"
# Look for: "State: Clean Shutdown" (good) vs "Dirty Shutdown" (needs repair)
```

---

## PROBLEM: ActiveSync Not Working

```powershell
# Step 1: Check if ActiveSync is enabled for user
Get-CASMailbox -Identity "jsmith" | Select ActiveSyncEnabled,ActiveSyncMailboxPolicy

# Enable ActiveSync for user
Set-CASMailbox -Identity "jsmith" -ActiveSyncEnabled $true

# Step 2: Check device partnerships
Get-MobileDeviceStatistics -Mailbox "jsmith" |
  Select DeviceFriendlyName,DeviceOS,LastSyncAttemptTime,Status

# Step 3: Check ActiveSync virtual directory
Get-ActiveSyncVirtualDirectory | Select InternalUrl,ExternalUrl,BasicAuthEnabled,WindowsAuthEnabled

# Step 4: Test ActiveSync connectivity
Test-ActiveSyncConnectivity -MailboxCredential (Get-Credential) `
  -TrustAnySSLCertificate

# Step 5: Check SSL certificate covers ActiveSync URL
Get-ExchangeCertificate |
  Select Thumbprint,Services,Subject,@{N='SANs';E={$_.DnsNameList}} |
  Where {$_.Services -like "*IIS*"}

# Wipe a mobile device (CAUTION)
Clear-MobileDevice -Identity "jsmith\DeviceID" -Confirm:$false
```

---

## PROBLEM: Certificate Issues

```powershell
# List all Exchange certificates
Get-ExchangeCertificate |
  Select Thumbprint,Status,Services,Subject,NotAfter,Issuer |
  Sort NotAfter

# Check which cert is assigned to which service
Get-ExchangeCertificate | Where {$_.Services -ne "None"} |
  Select Thumbprint,Services,Subject,NotAfter

# Assign certificate to services
Enable-ExchangeCertificate -Thumbprint "ABC123DEF456..." `
  -Services IIS,SMTP -Force

# Check cert expiry (warn if < 60 days)
Get-ExchangeCertificate | Where {$_.NotAfter -lt (Get-Date).AddDays(60)} |
  Select Subject,NotAfter,Services
```

---

## KEY EVENT IDs — Application Log

| Event Source | Event ID | Description |
|---|---|---|
| MSExchangeTransport | 1006 | Message delivery failure |
| MSExchangeTransport | 9213 | Back pressure — disk space low |
| MSExchangeTransport | 15002 | Queue database error |
| MSExchangeIS | 1000 | Information Store started |
| MSExchangeIS | 9518 | Database mount failure |
| MSExchangeIS | 9519 | Database mount success |
| MSExchangeADAccess | 2600 | Cannot contact AD |
| MSExchangeADAccess | 2604 | AD topology service not running |
| MSExchangeOWA | 76 | OWA authentication failure |

```powershell
# Check critical Exchange events
Get-EventLog -LogName Application -Source `
  "MSExchangeTransport","MSExchangeIS","MSExchangeADAccess" `
  -EntryType Error -Newest 50 |
  Select TimeGenerated,Source,EventID,Message |
  Format-Table -Wrap

# Check System log for IIS errors
Get-EventLog -LogName System -Source W3SVC -EntryType Error -Newest 20
```

---

## DIAGNOSTIC COMMANDS QUICK REFERENCE

| Problem | First Command |
|---|---|
| Mail not arriving | `Get-Queue \| Where {$_.MessageCount -gt 0}` |
| OWA down | `Get-Service W3SVC; iisreset /status` |
| DB dismounted | `Get-MailboxDatabase -Status \| Select Name,Mounted` |
| Transport stuck | `Get-Service MSExchangeTransport` |
| User can't send | `Get-Mailbox x \| Select *Quota*` |
| ActiveSync broken | `Get-CASMailbox x \| Select ActiveSyncEnabled` |
| Message lost | `Get-MessageTrackingLog -Recipients x -Start (Get-Date).AddDays(-1)` |
| Cert expiring | `Get-ExchangeCertificate \| Select Subject,NotAfter,Services` |
| Spam getting through | `Get-ContentFilterConfig` |
| All services | `Test-ServiceHealth` |
