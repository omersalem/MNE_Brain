# Mail Flow, Queues & Tracking — Exchange Server 2019
## PowerShell (EMS) + GUI

---

## MAIL FLOW — PowerShell

### Queues — Read (Safe)

```powershell
# View ALL queues
Get-Queue

# View queues with messages (not empty)
Get-Queue | Where {$_.MessageCount -gt 0} |
  Select Identity,Status,MessageCount,NextHopDomain,LastError

# View queue details
Get-Queue -Identity "EXCHANGE-SRV\Submission"
Get-Queue -Identity "EXCHANGE-SRV\Unreachable"

# View MESSAGES inside a queue
Get-Message -Queue "EXCHANGE-SRV\Unreachable" |
  Select Identity,Subject,FromAddress,ToAddress,DateReceived,Status,LastError |
  Select -First 50

# View messages across ALL queues
Get-Message -ResultSize Unlimited |
  Select Queue,Subject,FromAddress,ToAddress,DateReceived,Status

# Check delivery queue by domain
Get-Queue | Where {$_.NextHopDomain -like "*gmail.com*"}

# Transport service stats
Get-TransportService | Select Name,MaxOutboundConnections,MaxPerDomainOutboundConnections

# Check send/receive connectors
Get-ReceiveConnector | Select Name,Enabled,Bindings,PermissionGroups
Get-SendConnector | Select Name,Enabled,AddressSpaces,SmartHosts,DNSRoutingEnabled

# Check accepted domains
Get-AcceptedDomain | Select Name,DomainName,DomainType,Default

# Check remote domains
Get-RemoteDomain | Select Name,DomainName,AllowedOOFType,AutoReplyEnabled

# Check transport rules
Get-TransportRule | Select Name,State,Priority,Description | Sort Priority
```

### Queues — Manage (Require Confirmation)

```powershell
# ── RETRY delivery ──
Retry-Queue -Identity "EXCHANGE-SRV\Unreachable" -Resubmit $true
# Retry ALL queues
Get-Queue | Where {$_.Status -eq "Retry"} | Retry-Queue

# ── SUSPEND queue ──
Suspend-Queue -Identity "EXCHANGE-SRV\Submission"
Resume-Queue  -Identity "EXCHANGE-SRV\Submission"

# ── REMOVE messages from queue ──
# Remove specific message (with NDR bounce to sender)
Remove-Message -Identity "EXCHANGE-SRV\Unreachable\1234" -WithNDR $true -Confirm:$false

# Remove ALL messages from queue (no NDR)
Remove-Message -Queue "EXCHANGE-SRV\Unreachable" `
  -Filter {Subject -like "*spam*"} -WithNDR $false -Confirm:$false

# Remove ALL messages in queue (DANGEROUS)
Get-Message -Queue "EXCHANGE-SRV\Poison" |
  Remove-Message -WithNDR $false -Confirm:$false

# ── RESTART Transport service ──
Restart-Service MSExchangeTransport

# ── Force submission of messages in Pickup folder ──
# Place .eml file in: C:\Program Files\Microsoft\Exchange Server\V15\TransportRoles\Pickup\
```

---

## MESSAGE TRACKING — PowerShell

```powershell
# Basic tracking (last 24 hours)
Get-MessageTrackingLog `
  -Start (Get-Date).AddHours(-24) `
  -ResultSize Unlimited

# Track by SENDER
Get-MessageTrackingLog `
  -Sender "sender@external.com" `
  -Start  (Get-Date).AddHours(-24) `
  -ResultSize Unlimited |
  Select Timestamp,EventId,Source,Sender,Recipients,MessageSubject,TotalBytes

# Track by RECIPIENT
Get-MessageTrackingLog `
  -Recipients "jsmith@domain.com" `
  -Start (Get-Date).AddHours(-24) `
  -ResultSize Unlimited |
  Select Timestamp,EventId,Source,Sender,MessageSubject

# Track by SUBJECT
Get-MessageTrackingLog `
  -MessageSubject "Invoice #12345" `
  -Start (Get-Date).AddDays(-7) `
  -ResultSize Unlimited

# Full trace for a message (all hops)
Get-MessageTrackingLog `
  -MessageId "<abc123@domain.com>" `
  -ResultSize Unlimited |
  Select Timestamp,EventId,Source,ServerHostname,ConnectorId,Sender,Recipients

# Key EventId values:
# RECEIVE  — message received by transport
# DELIVER  — message delivered to mailbox
# SEND     — message sent to next hop
# FAIL     — delivery failed
# DEFER    — delivery deferred (will retry)
# EXPAND   — distribution group expanded
# REDIRECT — message redirected
# RESOLVE  — recipient email resolved
# SUBMIT   — message submitted from mailbox

# Track all FAILED deliveries today
Get-MessageTrackingLog `
  -EventId FAIL `
  -Start (Get-Date).Date `
  -ResultSize Unlimited |
  Select Timestamp,Sender,Recipients,MessageSubject,SourceContext

# Test mail flow
Test-MailFlow -TargetMailboxServer "EXCHANGE-SRV"
Test-MailFlow -TargetEmailAddress "jsmith@domain.com"
```

---

## TRANSPORT RULES — PowerShell

```powershell
# List all transport rules
Get-TransportRule | Select Name,State,Priority | Sort Priority

# Get rule details
Get-TransportRule -Identity "Add Disclaimer" | Format-List

# Create disclaimer rule
New-TransportRule -Name "Email Disclaimer" `
  -ApplyHtmlDisclaimerText @"
<p style='font-size:11px;color:gray;'>
This email is confidential. If received in error, please delete immediately.
</p>
"@ `
  -ApplyHtmlDisclaimerLocation Append `
  -ApplyHtmlDisclaimerFallbackAction Wrap `
  -Enabled $true

# Create rule: block external email with specific subject
New-TransportRule -Name "Block Phishing Keyword" `
  -FromScope NotInOrganization `
  -SubjectContainsWords "urgent wire transfer","account suspended" `
  -RejectMessageReasonText "This message was blocked by email policy." `
  -Enabled $true

# Create rule: copy all outbound mail to compliance
New-TransportRule -Name "Compliance BCC" `
  -FromScope InOrganization `
  -ToScope NotInOrganization `
  -BlindCopyTo "compliance@domain.com" `
  -Enabled $true

# Enable / Disable rule
Enable-TransportRule  -Identity "Add Disclaimer"
Disable-TransportRule -Identity "Add Disclaimer"

# Change rule priority
Set-TransportRule -Identity "Block Phishing Keyword" -Priority 0

# Remove rule
Remove-TransportRule -Identity "OldRule" -Confirm:$false
```

---

## CONNECTORS — PowerShell

```powershell
# ── RECEIVE CONNECTORS ──
# List receive connectors
Get-ReceiveConnector | Select Name,Enabled,Bindings,AuthMechanism,PermissionGroups

# Get specific connector
Get-ReceiveConnector -Identity "EXCHANGE-SRV\Default Frontend EXCHANGE-SRV"

# Allow relay from specific IP (SMTP relay for printer/application)
New-ReceiveConnector -Name "SMTP Relay - Printers" `
  -TransportRole FrontendTransport `
  -RemoteIPRanges 192.168.1.0/24 `
  -Bindings 0.0.0.0:25 `
  -PermissionGroups AnonymousUsers `
  -AuthMechanism ExternalAuthoritative

# !! After creating relay connector, set permissions:
Get-ReceiveConnector "SMTP Relay - Printers" |
  Add-ADPermission -User "NT AUTHORITY\ANONYMOUS LOGON" `
  -ExtendedRights "Ms-Exch-SMTP-Accept-Any-Recipient"

# ── SEND CONNECTORS ──
Get-SendConnector | Select Name,Enabled,AddressSpaces,SmartHosts,DNSRoutingEnabled

# Create internet send connector
New-SendConnector -Name "Internet Send Connector" `
  -AddressSpaces * `
  -DNSRoutingEnabled $true `
  -Internet `
  -SourceTransportServers "EXCHANGE-SRV"

# Create send connector via smarthost
New-SendConnector -Name "Via SmartHost" `
  -AddressSpaces * `
  -SmartHosts "smtp.isp.com" `
  -DNSRoutingEnabled $false `
  -SmartHostAuthMechanism BasicAuth `
  -AuthenticationCredential (Get-Credential)
```

---

## MAIL FLOW — GUI

### Queue Viewer (Exchange Toolbox)
```
Start → Microsoft Exchange Server 2019 → Exchange Toolbox → Queue Viewer

Main view:
  ┌──────────────────────────────────────────────────────────┐
  │ Queue Name          │ Status  │ Messages │ Next Retry    │
  │ Submission          │ Ready   │ 0        │               │
  │ Unreachable         │ Retry   │ 45       │ 12:30:00      │
  │ Poison              │ Suspend │ 2        │               │
  └──────────────────────────────────────────────────────────┘

Right-click queue:
  → Retry    (try delivery now)
  → Suspend  (stop processing)
  → Resume   (resume after suspend)

Click queue → see messages in bottom panel
Right-click message:
  → Remove (with NDR)    ← sends bounce to sender
  → Remove (without NDR) ← silently deletes
  → Suspend / Resume
  → Properties           ← full message details
```

### Transport Rules (EAC)
```
EAC → mail flow → rules
  + New → [select template or blank]

  Templates:
    - Apply disclaimers
    - Filter messages by sender/recipient
    - Bypass clutter
    - Generate incident report
    - Restrict large messages
    - Require TLS encryption

  Building custom rule:
    Name: [rule name]
    
    *Apply this rule if...
      (condition):
        The sender is...
        The recipient is...
        The subject includes...
        The message size is greater than...
        The sender domain is...
    
    *Do the following...
      (action):
        Add disclaimer...
        Redirect to...
        Delete the message...
        Require TLS
        Add header
        Blind carbon copy to...
        Block message / reject with explanation
    
    Except if... (exceptions)
    Priority: [number — lower = higher priority]
    Activate this rule on: [date]
    Deactivate this rule on: [date]
    Audit this rule with severity: Low/Medium/High
    
  → Save
```

### Delivery Reports / Message Tracking (EAC)
```
EAC → mail flow → delivery reports
  
  Search options:
    Search for messages sent to:    [recipient mailbox]
    Search for messages sent from:  [sender mailbox]
    
    Specify date range: From [date] to [date]
    Subject keywords: [optional]
  
  → Search
  
  Results show each message with:
    Status: Delivered / Pending / Failed
    Size, Subject, Time
  
  Click any message → Details panel shows:
    Every hop the message passed through
    Timestamp at each server/service
    Final delivery status and time
    Error message if failed
```
