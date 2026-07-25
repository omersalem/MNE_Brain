# Mailboxes — Exchange Server 2019
## PowerShell (EMS) + EAC GUI

---

## MAILBOXES — PowerShell (EMS)

### Read (Safe)

```powershell
# List all mailboxes
Get-Mailbox -ResultSize Unlimited |
  Select DisplayName,Alias,PrimarySmtpAddress,RecipientTypeDetails,Database

# Get specific mailbox
Get-Mailbox -Identity "jsmith"
Get-Mailbox -Identity "jsmith@domain.com"
Get-Mailbox -Identity "jsmith" | Format-List *

# Get mailbox size and statistics
Get-MailboxStatistics -Identity "jsmith" |
  Select DisplayName,TotalItemSize,ItemCount,DeletedItemCount,LastLogonTime,LastUserActionTime

# ALL mailboxes sorted by size (largest first)
Get-Mailbox -ResultSize Unlimited |
  Get-MailboxStatistics |
  Sort-Object TotalItemSize -Descending |
  Select DisplayName,TotalItemSize,ItemCount,Database |
  Select -First 20

# Check mailbox quota settings
Get-Mailbox -Identity "jsmith" |
  Select DisplayName,IssueWarningQuota,ProhibitSendQuota,`
         ProhibitSendReceiveQuota,UseDatabaseQuotaDefaults

# Find mailboxes OVER quota
Get-Mailbox -ResultSize Unlimited | ForEach {
  $stats = Get-MailboxStatistics $_
  $quota = (Get-Mailbox $_).ProhibitSendReceiveQuota
  if ($quota -ne "Unlimited") {
    [PSCustomObject]@{
      Name = $_.DisplayName
      Size = $stats.TotalItemSize
      Quota = $quota
    }
  }
} | Where {$_}

# Get all mailbox types
Get-Mailbox -RecipientTypeDetails UserMailbox -ResultSize Unlimited     # regular
Get-Mailbox -RecipientTypeDetails SharedMailbox -ResultSize Unlimited   # shared
Get-Mailbox -RecipientTypeDetails RoomMailbox -ResultSize Unlimited     # rooms
Get-Mailbox -RecipientTypeDetails EquipmentMailbox -ResultSize Unlimited # equipment

# Get mailbox permissions (Full Access)
Get-MailboxPermission -Identity "jsmith" |
  Where {$_.AccessRights -eq "FullAccess" -and $_.IsInherited -eq $false}

# Get Send-As permissions
Get-RecipientPermission -Identity "jsmith" |
  Where {$_.AccessRights -eq "SendAs" -and $_.Trustee -ne "NT AUTHORITY\SELF"}

# Get Send on Behalf
Get-Mailbox -Identity "jsmith" |
  Select DisplayName,GrantSendOnBehalfTo

# Check Out of Office status
Get-MailboxAutoReplyConfiguration -Identity "jsmith"

# Check CAS (client access) settings: OWA, ActiveSync, MAPI, POP, IMAP
Get-CASMailbox -Identity "jsmith" |
  Select OWAEnabled,ActiveSyncEnabled,MAPIEnabled,POPEnabled,IMAPEnabled,EWSEnabled

# Get email addresses (primary + aliases)
Get-Mailbox -Identity "jsmith" | Select -ExpandProperty EmailAddresses

# Audit mailbox access (who accessed it)
Get-MailboxAuditLog -Identity "jsmith" -LogonTypes Delegate,Admin -ResultSize 20 |
  Select Operation,LogonUserDisplayName,LastAccessed,OperationResult
```

### Create Mailboxes (Require Confirmation)

```powershell
# Create new user mailbox
New-Mailbox `
  -Name               "John Smith" `
  -Alias              "jsmith" `
  -FirstName          "John" `
  -LastName           "Smith" `
  -DisplayName        "John Smith" `
  -UserPrincipalName  "jsmith@domain.com" `
  -SamAccountName     "jsmith" `
  -Password           (ConvertTo-SecureString "P@ssword123!" -AsPlainText -Force) `
  -ResetPasswordOnNextLogon $true `
  -Database           "Mailbox Database 0001" `
  -OrganizationalUnit "OU=Users,DC=domain,DC=com"

# Enable mailbox for existing AD user
Enable-Mailbox -Identity "jsmith" -Database "Mailbox Database 0001"

# Create SHARED mailbox
New-Mailbox -Shared `
  -Name               "IT Support" `
  -Alias              "itsupport" `
  -DisplayName        "IT Support" `
  -UserPrincipalName  "itsupport@domain.com" `
  -PrimarySmtpAddress "itsupport@domain.com"

# Convert USER mailbox to SHARED
Set-Mailbox -Identity "jsmith" -Type Shared

# Convert SHARED back to USER
Set-Mailbox -Identity "itsupport" -Type Regular

# Create ROOM mailbox
New-Mailbox -Room `
  -Name               "Conference Room A" `
  -Alias              "conf-room-a" `
  -UserPrincipalName  "conf-room-a@domain.com" `
  -ResourceCapacity   20

# Create EQUIPMENT mailbox
New-Mailbox -Equipment `
  -Name           "Projector-01" `
  -Alias          "projector01" `
  -UserPrincipalName "projector01@domain.com"
```

### Modify Mailboxes (Require Confirmation)

```powershell
# Set mailbox quota (override database default)
Set-Mailbox -Identity "jsmith" `
  -IssueWarningQuota         "4GB" `
  -ProhibitSendQuota         "5GB" `
  -ProhibitSendReceiveQuota  "6GB" `
  -UseDatabaseQuotaDefaults  $false

# Use database default quota
Set-Mailbox -Identity "jsmith" -UseDatabaseQuotaDefaults $true

# Add email alias
Set-Mailbox -Identity "jsmith" `
  -EmailAddresses @{Add="j.smith@domain.com"}

# Change primary email address
Set-Mailbox -Identity "jsmith" -PrimarySmtpAddress "johnsmith@domain.com"

# Set display name
Set-Mailbox -Identity "jsmith" -DisplayName "John Smith - IT"

# Enable/disable Out of Office
Set-MailboxAutoReplyConfiguration -Identity "jsmith" `
  -AutoReplyState Enabled `
  -InternalMessage "I am out of office until Jan 15. Contact helpdesk@domain.com." `
  -ExternalMessage "I am out of office. Please contact support@domain.com."

Set-MailboxAutoReplyConfiguration -Identity "jsmith" -AutoReplyState Disabled

# Grant FULL ACCESS to shared mailbox
Add-MailboxPermission -Identity "itsupport" `
  -User           "jsmith" `
  -AccessRights   FullAccess `
  -InheritanceType All `
  -AutoMapping    $true   # auto-mount in Outlook

# Remove Full Access
Remove-MailboxPermission -Identity "itsupport" `
  -User "jsmith" -AccessRights FullAccess -Confirm:$false

# Grant SEND AS permission
Add-RecipientPermission -Identity "itsupport" `
  -Trustee     "jsmith" `
  -AccessRights SendAs `
  -Confirm:$false

# Grant SEND ON BEHALF
Set-Mailbox -Identity "itsupport" `
  -GrantSendOnBehalfTo @{Add="jsmith"}

# Enable/Disable OWA
Set-CASMailbox -Identity "jsmith" -OWAEnabled $false
Set-CASMailbox -Identity "jsmith" -OWAEnabled $true

# Enable/Disable ActiveSync
Set-CASMailbox -Identity "jsmith" -ActiveSyncEnabled $false

# Enable mailbox audit logging
Set-Mailbox -Identity "jsmith" `
  -AuditEnabled $true `
  -AuditDelegate OpenFirstRunPopup,SendAs,SendOnBehalf,Create,Update,Move,MoveToDeletedItems,Delete,FolderBind `
  -AuditAdmin    OpenFirstRunPopup,SendAs,Create,Update,Move,MoveToDeletedItems,Delete

# Disable mailbox (keeps AD account, removes Exchange attributes)
Disable-Mailbox -Identity "jsmith" -Confirm:$false

# Remove mailbox AND AD account
Remove-Mailbox -Identity "jsmith" -Confirm:$false

# Move mailbox to different database
New-MoveRequest -Identity "jsmith" -TargetDatabase "Mailbox Database 0002"
Get-MoveRequest -Identity "jsmith"
Get-MoveRequestStatistics -Identity "jsmith"
```

---

## DISTRIBUTION GROUPS — PowerShell

```powershell
# List all distribution groups
Get-DistributionGroup -ResultSize Unlimited |
  Select Name,Alias,PrimarySmtpAddress,GroupType,ManagedBy

# Get group members
Get-DistributionGroupMember -Identity "IT-Team" | Select Name,PrimarySmtpAddress

# Create distribution group
New-DistributionGroup `
  -Name               "All Staff" `
  -Alias              "allstaff" `
  -DisplayName        "All Staff" `
  -PrimarySmtpAddress "allstaff@domain.com" `
  -Members            "jsmith","mjones" `
  -MemberJoinRestriction Closed `
  -MemberDepartRestriction Closed

# Add member
Add-DistributionGroupMember -Identity "All Staff" -Member "jsmith"

# Remove member
Remove-DistributionGroupMember -Identity "All Staff" -Member "jsmith" -Confirm:$false

# Create DYNAMIC distribution group (auto-membership)
New-DynamicDistributionGroup `
  -Name             "All Mailboxes" `
  -Alias            "allboxes" `
  -PrimarySmtpAddress "allboxes@domain.com" `
  -RecipientFilter  {RecipientType -eq 'UserMailbox' -and Enabled -eq $true}

# Preview members of dynamic group
$ddg = Get-DynamicDistributionGroup "All Mailboxes"
Get-Recipient -RecipientPreviewFilter $ddg.RecipientFilter
```

---

## MAILBOXES — EAC GUI

### Create New Mailbox
```
EAC (https://EXCHANGE-SRV/ecp)
→ recipients → mailboxes → + (New icon)
→ User mailbox

  ┌── New user ──────────────────────────────┐
  │ * Alias:           jsmith                │
  │ ○ New user                               │
  │ ● Existing user → Browse → select user   │
  │                                          │
  │ If new user:                             │
  │   First name / Last name                 │
  │   Display name                           │
  │   User logon: jsmith @ [domain.com]      │
  │   Password + Confirm                     │
  │                                          │
  │ Mailbox database: [Browse or leave auto] │
  └──────────────────────────────────────────┘
→ Save
```

### Edit Mailbox Properties (EAC)
```
EAC → recipients → mailboxes → click mailbox → edit (pencil ✏️)

  Tabs:
  ┌── general ────────── Display name, alias, hide from GAL checkbox
  │                      Org unit path
  │
  ├── mailbox usage ──── Current mailbox size (bar graph)
  │                      Storage quota settings:
  │                        ○ Use mailbox database defaults
  │                        ● Customize storage quotas:
  │                          Issue warning at: [GB]
  │                          Prohibit send at: [GB]
  │                          Prohibit send and receive: [GB]
  │
  ├── contact info ───── Phone, address, fax etc.
  │
  ├── organization ───── Title, department, company, manager, direct reports
  │
  ├── email address ──── All SMTP addresses
  │                      + Add alias | Set as primary
  │                      SMTP: primary (bold), smtp: secondary
  │
  ├── mailbox features ─ Enable/Disable:
  │                        OWA (Outlook Web App)
  │                        Exchange ActiveSync
  │                        MAPI (Outlook connectivity)
  │                        POP3
  │                        IMAP4
  │                        Archiving
  │
  ├── member of ──────── Distribution group membership (read-only view)
  │
  ├── MailTip ────────── Custom message shown to senders in Outlook
  │
  └── mailbox delegation
        Full Access → + add user / - remove user
        Send As     → + add user / - remove user
        Send on Behalf → + add user
→ Save
```

### Create Shared Mailbox (EAC)
```
EAC → recipients → shared → + (New)
  Display name: IT Support
  Email address: itsupport @ domain.com
  Alias: itsupport
→ Save

Then assign permissions:
  EAC → recipients → shared → click "IT Support" → edit
  → mailbox delegation → Full Access → + → add users → Save
```

### Search / Find Mailbox (EAC)
```
EAC → recipients → mailboxes
  Search box (top right): type name, alias, or email
  Filter: click ▼ next to search for advanced filters
    - Type: User / Shared / Room / Equipment / All
    - Status: Enabled / Disabled
```
