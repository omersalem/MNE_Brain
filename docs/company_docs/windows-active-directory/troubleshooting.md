# Troubleshooting — Active Directory
## Windows Server 2019

---

## COMMON PROBLEMS & DIAGNOSTICS

### Problem: User Cannot Log In

```powershell
# Step 1: Check account status comprehensively
Get-ADUser -Identity "jsmith" -Properties `
  Enabled,LockedOut,BadLogonCount,BadPasswordTime,`
  LastBadPasswordAttempt,PasswordExpired,PasswordLastSet,`
  AccountExpirationDate,LockedOut,UserAccountControl |
  Format-List

# Step 2: Unlock if locked
Unlock-ADAccount -Identity "jsmith"

# Step 3: Reset password if expired
Set-ADAccountPassword -Identity "jsmith" -Reset `
  -NewPassword (ConvertTo-SecureString $env:MNE_READONLY_SECRET -AsPlainText -Force)
Set-ADUser -Identity "jsmith" -ChangePasswordAtLogon $true

# Step 4: Check group membership (required for logon restrictions)
Get-ADPrincipalGroupMembership -Identity "jsmith" | Select Name

# Step 5: Check which DC authenticated the user last
Get-WinEvent -ComputerName DC01 `
  -FilterHashtable @{LogName='Security'; Id=4624} -MaxEvents 100 |
  Where {$_.Message -like "*jsmith*"}

# Step 6: Check for login time restrictions
Get-ADUser -Identity "jsmith" -Properties LogonHours | Select LogonHours

# Step 7: Verify Kerberos works
klist purge          # clear Kerberos tickets on client
klist               # list current tickets
nltest /sc_verify:domain.com   # verify secure channel

# Step 8: Check netlogon log on DC
Get-Content "C:\Windows\debug\netlogon.log" | Select-Object -Last 100 |
  Select-String "jsmith"
```

---

### Problem: AD Replication Failure

```powershell
# Step 1: Quick summary
repadmin /replsummary

# Step 2: Show errors only
repadmin /showrepl * /errorsonly

# Step 3: Detailed replication status
repadmin /showrepl DC01

# Step 4: Check event logs for replication errors
Get-WinEvent -ComputerName DC01 `
  -FilterHashtable @{LogName='Directory Service'; Level=2} -MaxEvents 20 |
  Select TimeCreated,Id,Message

# Step 5: Force replication
repadmin /syncall DC01 /AdeP

# Step 6: Force replication on specific partition
repadmin /replicate DC02 DC01 "dc=domain,dc=com"

# Step 7: Check RPC connectivity between DCs
portqry -n DC02 -e 135           # RPC endpoint mapper
portqry -n DC02 -r 1024-5000     # dynamic RPC ports

# Step 8: Check time sync (critical for Kerberos/replication)
w32tm /query /status
w32tm /stripchart /computer:DC01 /samples:5
# Fix time sync:
net stop w32time
w32tm /unregister
w32tm /register
net start w32time
w32tm /resync /force
```

---

### Problem: Domain Controller Health Check (Full)

```powershell
# Complete health check sequence
Write-Host "=== 1. DCDIAG ===" -ForegroundColor Cyan
dcdiag /v /c 2>&1 | Tee-Object -FilePath "C:\dc-health.txt"

Write-Host "=== 2. REPLICATION SUMMARY ===" -ForegroundColor Cyan
repadmin /replsummary

Write-Host "=== 3. FSMO ROLES ===" -ForegroundColor Cyan
netdom query fsmo

Write-Host "=== 4. SERVICES ===" -ForegroundColor Cyan
Get-Service -ComputerName DC01 `
  -Name NTDS,Netlogon,DFSR,DNS,KDC,W32Time |
  Select DisplayName,Status

Write-Host "=== 5. DC SYSVOL SHARE ===" -ForegroundColor Cyan
net view \\DC01

Write-Host "=== 6. DNS REGISTRATION ===" -ForegroundColor Cyan
nslookup -type=SRV _kerberos._tcp.domain.com
nslookup -type=SRV _ldap._tcp.domain.com

Write-Host "=== 7. SECURE CHANNEL ===" -ForegroundColor Cyan
nltest /sc_verify:domain.com
nltest /dsgetdc:domain.com
```

---

### Problem: Lockout Storm (Many Users Being Locked)

```powershell
# Find where lockouts are coming from (Event 4740 on PDC)
$PDC = (Get-ADDomain).PDCEmulator
Get-WinEvent -ComputerName $PDC `
  -FilterHashtable @{LogName='Security'; Id=4740} -MaxEvents 100 |
  Select TimeCreated,
    @{N='LockedAccount';E={$_.Properties[0].Value}},
    @{N='CallerComputer';E={$_.Properties[1].Value}} |
  Sort TimeCreated -Descending

# Find locked accounts
Search-ADAccount -LockedOut |
  Select Name,SamAccountName,LastLogonDate,LockedOut,BadLogonCount

# Unlock all (after finding root cause)
Search-ADAccount -LockedOut | Unlock-ADAccount

# Check password policy
Get-ADDefaultDomainPasswordPolicy
```

---

### Problem: GPO Not Applying

```powershell
# On the client machine:
# Step 1: Force update
gpupdate /force

# Step 2: Check results
gpresult /r

# Step 3: Verbose HTML report
gpresult /h C:\gpresult.html

# Step 4: Check event logs
Get-WinEvent -LogName "System" -FilterHashtable @{Id=1500,1501,1502,1503,7016} |
  Select TimeCreated,Id,Message

# Step 5: Check DNS (GPO relies on AD DNS)
nslookup domain.com
nslookup DC01.domain.com

# Step 6: Check RPC (GPO downloads via SMB/RPC)
net use \\DC01\SYSVOL  # can you reach SYSVOL?

# On the DC — check GPO replication:
Get-DfsrState -ComputerName DC01
```

---

### Problem: SYSVOL Not Replicating

```powershell
# Check DFSR replication state
Get-DfsrState -ComputerName DC01
Get-DfsrState -ComputerName DC02

# Check DFSR service
Get-Service -Name DFSR -ComputerName DC01,DC02

# Check DFSR event log
Get-WinEvent -ComputerName DC01 `
  -LogName "DFS Replication" -MaxEvents 50 |
  Where {$_.Level -le 3} | Select TimeCreated,Id,Message

# Force DFSR poll
(Get-WmiObject -Namespace root\MicrosoftDFS `
  -Class DfsrConfig -ComputerName DC01).PollDsNow()

# Verify SYSVOL shares exist
net view \\DC01 | Select-String "SYSVOL|NETLOGON"
```

---

## KEY EVENT IDs — Security Log

| Event ID | Description | Where to Look |
|---|---|---|
| 4624 | Successful logon | Security log on DC |
| 4625 | Failed logon (wrong password) | Security log on DC |
| 4740 | Account locked out | Security log on **PDC Emulator** |
| 4720 | User account created | Security log on DC |
| 4722 | User account enabled | Security log |
| 4723 | Password change attempt | Security log |
| 4724 | Admin reset password | Security log |
| 4725 | User account disabled | Security log |
| 4726 | User account deleted | Security log |
| 4728 | Member added to global group | Security log |
| 4729 | Member removed from global group | Security log |
| 4732 | Member added to local group | Security log |
| 4756 | Member added to universal group | Security log |
| 4768 | Kerberos TGT request | Security log on DC |
| 4769 | Kerberos service ticket request | Security log on DC |
| 4771 | Kerberos pre-auth failed | Security log on DC |
| 4776 | NTLM auth attempt | Security log on DC |

```powershell
# Query any Event ID
Get-WinEvent -ComputerName DC01 `
  -FilterHashtable @{LogName='Security'; Id=4740} |
  Select TimeCreated,
    @{N='Account';E={$_.Properties[0].Value}},
    @{N='CallerComputer';E={$_.Properties[1].Value}} |
  Select -First 20

# Query Directory Service log (replication errors)
Get-WinEvent -ComputerName DC01 -LogName "Directory Service" `
  -MaxEvents 50 | Where {$_.Level -le 3}

# Query System log for Netlogon errors
Get-WinEvent -ComputerName DC01 -LogName System `
  -FilterHashtable @{ProviderName='NETLOGON'} -MaxEvents 20
```

---

## DIAGNOSTIC TOOLKIT QUICK REFERENCE

| Tool | Command | Purpose |
|---|---|---|
| dcdiag | `dcdiag /v` | Full DC health |
| repadmin | `repadmin /replsummary` | Replication health |
| netdom | `netdom query fsmo` | FSMO roles |
| nltest | `nltest /sc_verify:domain.com` | Secure channel |
| gpresult | `gpresult /r` | GPO application |
| gpupdate | `gpupdate /force` | Force GPO refresh |
| w32tm | `w32tm /query /status` | Time sync |
| portqry | `portqry -n DC01 -e 389` | LDAP port check |
| klist | `klist purge` | Kerberos tickets |
| nslookup | `nslookup -type=SRV _ldap._tcp.domain.com` | DNS SRV records |
