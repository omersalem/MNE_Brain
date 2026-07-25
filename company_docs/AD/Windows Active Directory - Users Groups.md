# Users & Groups — Active Directory
## Windows Server 2019

---

## USERS — PowerShell

### Read (Safe)

```powershell
# List all users with key properties
Get-ADUser -Filter * -Properties DisplayName,EmailAddress,Department,Title,`
  LastLogonDate,Enabled,LockedOut,PasswordLastSet,PasswordExpired |
  Select SamAccountName,DisplayName,Enabled,LockedOut,PasswordExpired,LastLogonDate,Department

# Find specific user (multiple methods)
Get-ADUser -Identity "jsmith"
Get-ADUser -Identity "jsmith" -Properties *
Get-ADUser -Filter {Name -like "*Smith*"}
Get-ADUser -Filter {EmailAddress -eq "jsmith@domain.com"}
Get-ADUser -Filter {SamAccountName -eq "jsmith"}

# Find ALL locked-out accounts
Search-ADAccount -LockedOut |
  Select Name,SamAccountName,LockedOut,BadLogonCount,LastLogonDate

# Find disabled accounts
Search-ADAccount -AccountDisabled | Select Name,SamAccountName,LastLogonDate

# Find accounts with expired passwords
Search-ADAccount -PasswordExpired | Select Name,SamAccountName

# Find accounts with password never expires
Get-ADUser -Filter {PasswordNeverExpires -eq $true} -Properties PasswordNeverExpires |
  Select Name,SamAccountName,PasswordNeverExpires

# Find inactive users — no login for 90 days
$date = (Get-Date).AddDays(-90)
Get-ADUser -Filter {LastLogonDate -lt $date -and Enabled -eq $true} `
  -Properties LastLogonDate | Select Name,SamAccountName,LastLogonDate

# Find accounts expiring soon (next 30 days)
$soon = (Get-Date).AddDays(30)
Search-ADAccount -AccountExpiring -TimeSpan 30 | Select Name,SamAccountName

# Check single user full details
Get-ADUser -Identity "jsmith" -Properties * | Format-List

# Check if user is locked and why
Get-ADUser -Identity "jsmith" `
  -Properties LockedOut,BadLogonCount,BadPasswordTime,LastBadPasswordAttempt,PasswordExpired,AccountExpirationDate |
  Select Name,LockedOut,BadLogonCount,LastBadPasswordAttempt,PasswordExpired,AccountExpirationDate

# Get user group membership
Get-ADPrincipalGroupMembership -Identity "jsmith" | Select Name,GroupCategory,GroupScope

# Get user photo
Get-ADUser -Identity "jsmith" -Properties thumbnailPhoto

# List users in specific OU
Get-ADUser -Filter * -SearchBase "OU=IT,DC=domain,DC=com" |
  Select SamAccountName,Name,Enabled
```

### Modify — Users (Require Confirmation)

```powershell
# ── UNLOCK ──
Unlock-ADAccount -Identity "jsmith"
# Unlock ALL locked accounts at once
Search-ADAccount -LockedOut | Unlock-ADAccount

# ── PASSWORD ──
# Reset password
Set-ADAccountPassword -Identity "jsmith" -Reset `
  -NewPassword (ConvertTo-SecureString "NewP@ss123!" -AsPlainText -Force)

# Reset password + force change at next logon
Set-ADAccountPassword -Identity "jsmith" -Reset `
  -NewPassword (ConvertTo-SecureString "NewP@ss123!" -AsPlainText -Force)
Set-ADUser -Identity "jsmith" -ChangePasswordAtLogon $true

# Set password never expires
Set-ADUser -Identity "jsmith" -PasswordNeverExpires $true

# ── ENABLE / DISABLE ──
Enable-ADAccount -Identity "jsmith"
Disable-ADAccount -Identity "jsmith"

# ── CREATE ──
New-ADUser `
  -Name             "John Smith" `
  -GivenName        "John" `
  -Surname          "Smith" `
  -SamAccountName   "jsmith" `
  -UserPrincipalName "jsmith@domain.com" `
  -EmailAddress     "jsmith@domain.com" `
  -Path             "OU=Users,OU=IT,DC=domain,DC=com" `
  -AccountPassword  (ConvertTo-SecureString "P@ssword123!" -AsPlainText -Force) `
  -Enabled          $true `
  -Department       "IT" `
  -Title            "Engineer" `
  -ChangePasswordAtLogon $true

# ── MODIFY ──
Set-ADUser -Identity "jsmith" `
  -Department  "IT" `
  -Title       "Senior Engineer" `
  -Office      "HQ" `
  -Manager     (Get-ADUser "mjones") `
  -Description "Network Engineer"

# ── MOVE ──
Move-ADObject `
  -Identity    (Get-ADUser "jsmith").DistinguishedName `
  -TargetPath  "OU=NewOU,DC=domain,DC=com"

# ── EXPIRATION ──
Set-ADAccountExpiration -Identity "jsmith" -DateTime "12/31/2025"
Clear-ADAccountExpiration -Identity "jsmith"

# ── BULK OPERATIONS ──
# Disable all users in specific OU
Get-ADUser -Filter * -SearchBase "OU=Leavers,DC=domain,DC=com" |
  Disable-ADAccount

# Export all users to CSV
Get-ADUser -Filter * -Properties DisplayName,EmailAddress,Department,Title,LastLogonDate,Enabled |
  Select SamAccountName,DisplayName,EmailAddress,Department,Title,LastLogonDate,Enabled |
  Export-Csv "C:\AD-Users-Export.csv" -NoTypeInformation

# ── DELETE ──
# Best practice: Disable first, then delete after review period
Disable-ADAccount -Identity "jsmith"
Remove-ADUser -Identity "jsmith" -Confirm:$false
```

---

## GROUPS — PowerShell

### Read (Safe)

```powershell
# List all groups
Get-ADGroup -Filter * | Select Name,GroupScope,GroupCategory,Description

# Find group
Get-ADGroup -Identity "IT-Admins"
Get-ADGroup -Filter {Name -like "*Admin*"}

# Get group members
Get-ADGroupMember -Identity "IT-Admins" | Select Name,SamAccountName,ObjectClass

# Recursive (includes nested groups)
Get-ADGroupMember -Identity "IT-Admins" -Recursive | Select Name,SamAccountName

# Find empty groups
Get-ADGroup -Filter * |
  Where { -not (Get-ADGroupMember $_ -ErrorAction SilentlyContinue) } |
  Select Name

# Find user's group memberships (recursive)
Get-ADPrincipalGroupMembership -Identity "jsmith" |
  Select Name,GroupScope,GroupCategory

# Find groups with no manager set
Get-ADGroup -Filter * -Properties ManagedBy | Where {!$_.ManagedBy} | Select Name

# Find large groups (more than 50 members)
Get-ADGroup -Filter * |
  Where { (Get-ADGroupMember $_ -ErrorAction SilentlyContinue).Count -gt 50 } |
  Select Name
```

### Modify — Groups (Require Confirmation)

```powershell
# ── CREATE ──
New-ADGroup `
  -Name         "IT-Network" `
  -GroupScope   "Global" `
  -GroupCategory "Security" `
  -Path         "OU=Groups,DC=domain,DC=com" `
  -Description  "Network Team Security Group"

# ── ADD MEMBER ──
Add-ADGroupMember -Identity "IT-Admins" -Members "jsmith"
Add-ADGroupMember -Identity "IT-Admins" -Members "jsmith","mjones","bwilson"
# Add group to another group (nesting)
Add-ADGroupMember -Identity "All-IT" -Members "IT-Admins"

# ── REMOVE MEMBER ──
Remove-ADGroupMember -Identity "IT-Admins" -Members "jsmith" -Confirm:$false

# ── SYNC group from CSV ──
$members = Import-Csv "C:\group-members.csv"
$members | ForEach { Add-ADGroupMember -Identity "IT-Admins" -Members $_.SamAccountName }

# ── DELETE ──
Remove-ADGroup -Identity "OldGroup" -Confirm:$false
```

---

## USERS — GUI (ADUC — dsa.msc)

### Enable Advanced Features (Do This First)
```
ADUC → View menu → ✅ Advanced Features
```
Reveals: Attribute Editor tab, LostAndFound, System containers.

### Create New User
```
ADUC → Navigate to target OU
Right-click OU → New → User
  ┌─────────────────────────────────┐
  │ First name:    John             │
  │ Last name:     Smith            │
  │ Full name:     John Smith       │
  │ User logon:    jsmith@domain.com│
  │ Pre-Win2000:   jsmith           │
  └─────────────────────────────────┘
→ Next
  ┌─────────────────────────────────┐
  │ Password:        ••••••••       │
  │ Confirm:         ••••••••       │
  │ ☑ User must change at next logon│
  │ ☐ User cannot change password   │
  │ ☐ Password never expires        │
  │ ☐ Account is disabled           │
  └─────────────────────────────────┘
→ Next → Finish
```

### Reset Password
```
ADUC → find user → Right-click → Reset Password
  New password + Confirm
  ☑ User must change password at next logon
  ☑ Unlock the user's account   ← CHECK THIS if user is locked
→ OK
```

### Unlock Account
```
Method 1: Right-click user → Reset Password → check "Unlock account"
Method 2: Double-click user → Properties → Account tab
          → ☑ Unlock account → OK
```

### Edit User Properties (All Tabs)
```
ADUC → Double-click user → Properties
  ┌── General ──────── Name, description, office, phone, email, web page
  ├── Address ──────── Street, PO Box, city, state, zip, country
  ├── Account ──────── UPN logon, logon hours, logon workstations,
  │                    account options (pwd never expires etc.), expiry
  ├── Profile ──────── Profile path \\server\profiles\%username%
  │                    Logon script, home folder
  ├── Telephones ───── Phone numbers (various)
  ├── Organization ─── Title, department, company, manager, direct reports
  ├── Member Of ─────── Group membership → Add / Remove
  ├── Dial-in ──────── Remote access permissions
  ├── Environment ──── Terminal Services settings
  ├── Sessions ─────── TS session timeout settings
  ├── Remote Control ─ TS remote control settings
  ├── Remote Desktop ─ RD Services profile
  ├── COM+ ────────────
  └── Attribute Editor ← (Advanced view only) ALL LDAP attributes directly
```

### Move User
```
ADUC → Right-click user → Move
  → Browse to target OU → OK
```

### Find / Search Users
```
ADUC → Right-click domain or OU → Find
  Find: Users, Contacts, and Groups
  Name: [search term]
  Or: Advanced tab → Field → User → [any LDAP attribute] → Condition → Value
→ Find Now
```

### Disable / Enable / Delete
```
Disable:  Right-click user → Disable Account   (icon gets grey X)
Enable:   Right-click user → Enable Account
Delete:   Right-click user → Delete → Yes
          ⚠️ Best practice: disable first, delete after 30 days
```

---

## GROUPS — GUI (ADUC)

### Create Group
```
ADUC → target OU → Right-click → New → Group
  Group name:     IT-Network
  Group scope:    ● Global   (recommended for users)
                  ○ Domain local  (for resources)
                  ○ Universal     (cross-domain)
  Group type:     ● Security  (access control)
                  ○ Distribution  (email only)
→ OK
```

### Add Members to Group
```
ADUC → Double-click group → Properties → Members tab
  → Add → type username → Check Names → OK → Apply
```

### View User's Groups
```
ADUC → Double-click user → Properties → Member Of tab
  Shows all groups → Add / Remove from here
```

### Convert Group Type/Scope
```
ADUC → Double-click group → Properties → General tab
  Group scope and type can be changed here
  ⚠️ Some conversions are restricted by AD rules
```
