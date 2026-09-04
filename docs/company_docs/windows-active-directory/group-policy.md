# Group Policy (GPO) — Active Directory
## Windows Server 2019

---

## GROUP POLICY — PowerShell

```powershell
# Requires: Install-WindowsFeature GPMC
Import-Module GroupPolicy

# List all GPOs in domain
Get-GPO -All | Select DisplayName,GpoStatus,CreationTime,ModificationTime

# Get specific GPO
Get-GPO -Name "Default Domain Policy"
Get-GPO -Guid "{31B2F340-016D-11D2-945F-00C04FB984F9}"

# Get GPO links on an OU
Get-GPInheritance -Target "OU=IT,DC=domain,DC=com"

# Get all GPOs linked to a specific OU
(Get-GPInheritance -Target "OU=IT,DC=domain,DC=com").GpoLinks

# Get GPO report (HTML)
Get-GPOReport -Name "Default Domain Policy" -ReportType HTML -Path "C:\GPO-Report.html"

# Get GPO report for ALL GPOs
Get-GPOReport -All -ReportType HTML -Path "C:\All-GPO-Reports.html"

# Backup a GPO
Backup-GPO -Name "Default Domain Policy" -Path "C:\GPO-Backups"

# Backup ALL GPOs
Backup-GPO -All -Path "C:\GPO-Backups"

# Restore GPO from backup
Restore-GPO -Name "Default Domain Policy" -Path "C:\GPO-Backups"

# Create new GPO
New-GPO -Name "IT Security Policy" -Comment "Security settings for IT OU"

# Link GPO to OU
New-GPLink -Name "IT Security Policy" -Target "OU=IT,DC=domain,DC=com"

# Link with enforced
New-GPLink -Name "IT Security Policy" `
  -Target "OU=IT,DC=domain,DC=com" `
  -LinkEnabled Yes `
  -Enforced Yes

# Remove GPO link (does not delete GPO)
Remove-GPLink -Name "IT Security Policy" -Target "OU=IT,DC=domain,DC=com"

# Delete GPO
Remove-GPO -Name "OldPolicy"

# Set GPO registry value
Set-GPRegistryValue -Name "IT Security Policy" `
  -Key "HKLM\Software\Policies\Microsoft\Windows\System" `
  -ValueName "DisableCMD" `
  -Type DWord -Value 1

# Force GPO update on remote computer
Invoke-GPUpdate -Computer "PC001" -Force -RandomDelayInMinutes 0

# Get GPO results for a user/computer
Get-GPResultantSetOfPolicy -Computer "PC001" -User "DOMAIN\jsmith" `
  -ReportType HTML -Path "C:\RSOP-Report.html"
```

---

## GROUP POLICY — GUI (gpmc.msc)

### Open GPMC
```
Server Manager → Tools → Group Policy Management
OR: Win+R → gpmc.msc
```

### GPMC Tree Structure
```
Group Policy Management
└── Forest: domain.com
      └── Domains
            └── domain.com
                  ├── Default Domain Policy    ← Password/lockout policy
                  ├── Default Domain Controllers Policy
                  ├── [Your Custom GPOs]
                  ├── Group Policy Objects
                  │     └── [All GPOs listed here]
                  ├── WMI Filters
                  ├── Starter GPOs
                  └── Sites
                        └── [Site-linked GPOs]
```

### Create and Link a New GPO
```
GPMC → right-click target OU → Create a GPO in this domain, and Link it here
  Name: "IT Security Policy"
  → OK
  
Then edit: right-click the new GPO → Edit
  Opens Group Policy Management Editor (GPME)
```

### Edit a GPO (GPME Layout)
```
Group Policy Management Editor:
├── Computer Configuration
│     ├── Policies
│     │     ├── Software Settings
│     │     │     └── Software Installation
│     │     ├── Windows Settings
│     │     │     ├── Name Resolution Policy
│     │     │     ├── Scripts (Startup/Shutdown)
│     │     │     └── Security Settings
│     │     │           ├── Account Policies
│     │     │           │     ├── Password Policy       ← min length, complexity
│     │     │           │     ├── Account Lockout Policy ← lockout threshold
│     │     │           │     └── Kerberos Policy
│     │     │           ├── Local Policies
│     │     │           │     ├── Audit Policy
│     │     │           │     ├── User Rights Assignment
│     │     │           │     └── Security Options
│     │     │           ├── Windows Firewall
│     │     │           └── Software Restriction Policies
│     │     └── Administrative Templates
│     │           └── [Hundreds of registry-based settings]
│     └── Preferences
│           └── [Drive maps, shortcuts, registry, etc.]
│
└── User Configuration
      ├── Policies
      │     ├── Software Settings
      │     ├── Windows Settings
      │     │     ├── Scripts (Logon/Logoff)
      │     │     ├── Security Settings
      │     │     └── Folder Redirection
      │     └── Administrative Templates
      │           ├── Control Panel
      │           ├── Desktop
      │           ├── Network
      │           └── Start Menu and Taskbar
      └── Preferences
            └── [User-level preferences]
```

### Common GPO Settings Locations

**Password Policy:**
```
Computer Configuration → Policies → Windows Settings →
Security Settings → Account Policies → Password Policy
  - Enforce password history: 24 passwords
  - Maximum password age: 90 days
  - Minimum password age: 1 day
  - Minimum password length: 12 characters
  - Password must meet complexity requirements: Enabled
```

**Account Lockout Policy:**
```
Computer Configuration → Policies → Windows Settings →
Security Settings → Account Policies → Account Lockout Policy
  - Account lockout duration: 30 minutes
  - Account lockout threshold: 5 invalid logon attempts
  - Reset account lockout counter after: 30 minutes
```

**Audit Policy (Security Logging):**
```
Computer Configuration → Policies → Windows Settings →
Security Settings → Local Policies → Audit Policy
  - Audit account logon events: Success, Failure
  - Audit account management: Success, Failure
  - Audit logon events: Success, Failure
  - Audit policy change: Success
```

**Disable USB storage:**
```
Computer Configuration → Policies → Administrative Templates →
System → Removable Storage Access
  - All Removable Storage classes: Deny all access: Enabled
```

**Map Network Drive (User Preference):**
```
User Configuration → Preferences → Windows Settings → Drive Maps
  New → Mapped Drive
    Action: Create (or Replace for idempotent)
    Location: \\server\share
    Reconnect: ✅
    Label: IT Share
    Drive letter: Z:
```

### GPO Enforcement and Blocking

**Enforce a GPO (cannot be blocked by child OUs):**
```
GPMC → right-click GPO link → Enforced ✅
Link shows lock icon when enforced
```

**Block GPO inheritance on an OU:**
```
GPMC → right-click OU → Block Inheritance ✅
OU shows blue exclamation icon
⚠️ Does not block Enforced GPOs
```

**GPO Link Order (priority):**
```
GPMC → click OU → Linked Group Policy Objects tab
  Higher link order number = LOWER priority
  Link Order 1 = highest priority (applied last, wins conflicts)
  Arrows to move GPOs up/down
```

### Check GPO Application (RSOP)

**From command line on client/server:**
```cmd
gpresult /r                      # text summary
gpresult /h C:\rsop.html         # HTML report
gpresult /scope computer /v      # verbose computer settings
gpresult /scope user /v          # verbose user settings
gpresult /user DOMAIN\jsmith /r  # for specific user
```

**From GPMC (for any computer/user):**
```
GPMC → Group Policy Results → right-click → Group Policy Results Wizard
  → Computer: PC001
  → User: DOMAIN\jsmith
  → Finish
  Shows exactly which GPOs applied, which were filtered, and why
```

**Force GPO refresh immediately:**
```cmd
gpupdate /force                      # current computer
gpupdate /force /logoff              # + logoff when done
gpupdate /force /boot                # + reboot when done
Invoke-GPUpdate -Computer "PC001" -Force   # PowerShell remote
```

### WMI Filters (GPO Targeting)
```
GPMC → WMI Filters → New
  Name: Windows 10 Only
  Query: SELECT * FROM Win32_OperatingSystem WHERE Version LIKE "10.%"
  
Then link to GPO:
  GPMC → click GPO → Scope tab → WMI Filtering → select filter
  ⚠️ WMI filter evaluation adds logon time — keep queries simple
```
