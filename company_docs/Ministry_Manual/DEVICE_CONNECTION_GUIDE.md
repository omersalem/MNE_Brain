# MNE Ministry — Device Connection & Troubleshooting Guide

> **Purpose:** Any AI assistant can connect to all ministry infrastructure devices in read-only mode and perform troubleshooting.
> **Access Method:** SSH for network devices, WinRM/PowerShell Remoting for Windows devices.
> **Credentials:** Provided per-device below. Use only **read-only** commands (`show`, `get`, `Get-*`, `Select-Object`, etc.).

---

## Table of Contents

1. [Connection Quick Reference](#1-connection-quick-reference)
2. [Windows Devices (WinRM / PowerShell)](#2-windows-devices-winrm--powershell)
3. [Network Devices (SSH)](#3-network-devices-ssh)
   - 3.1 FortiGate (FGT)
   - 3.2 Cisco FMC
   - 3.3 Cisco FTD
   - 3.4 F5 BIG-IP
   - 3.5 Cisco Core Switch
   - 3.6 Fujitsu PSWITCH
   - 3.7 vCenter
   - 3.8 Floor Switches (Cat9K Lite)
4. [FMC API (for policies)](#4-fmc-api-for-policies)
5. [General Troubleshooting Workflows](#5-general-troubleshooting-workflows)
6. [Common Issues & Commands](#6-common-issues--commands)

---

## 1. Connection Quick Reference

| # | Device | IP | Auth Method | Username | Password |
|---|--------|----|-------------|----------|----------|
| 1 | **FortiGate** (FGT) | 172.23.70.4 | SSH (port 22) | adminread | secret_ref("MNE_FORTIGATE_READONLY_CREDENTIAL") |
| 2 | **FMC** (Cisco FMC) | 172.23.70.77 | SSH → `expert` bash | admin | secret_ref("MNE_FMC_READONLY_CREDENTIAL") |
| 3 | **FTD** (Cisco FTD) | 172.23.70.78 | SSH (port 22) | admin | secret_ref("MNE_FTD_READONLY_CREDENTIAL") |
| 4 | **F5 BIG-IP** | 172.23.70.89 | SSH (port 22) | admin | secret_ref("MNE_F5_READONLY_CREDENTIAL") |
| 5 | **Active Directory** (MNE-DC1) | 172.23.71.27 | WinRM (port 5985) | MNE\admin | secret_ref("MNE_WINRM_READONLY_CREDENTIAL") |
| 6 | **DNS** (MNE-DC1) | 172.23.71.27 | WinRM (port 5985) | MNE\admin | secret_ref("MNE_WINRM_READONLY_CREDENTIAL") |
| 7 | **Exchange 2019** (EXCHAMGESRV2) | 172.23.71.36 | WinRM + Exchange PS | MNE\admin | secret_ref("MNE_WINRM_READONLY_CREDENTIAL") |
| 8 | **Fujitsu SW1** | 172.23.70.70 | SSH (port 22) | admin | secret_ref("MNE_FUJITSU_READONLY_CREDENTIAL") |
| 9 | **Fujitsu SW2** | 172.23.70.71 | SSH (port 22) | admin | secret_ref("MNE_FUJITSU_READONLY_CREDENTIAL") |
| 10 | **Cisco Core** (CoreSwitch1) | 172.23.70.254 | SSH (user exec only) | admin | secret_ref("MNE_CISCO_READONLY_CREDENTIAL") |
| 11 | **vCenter** (VCSA 7.0.3) | 172.23.69.38 | SSH → `shell` bash | root | secret_ref("MNE_VCENTER_READONLY_CREDENTIAL") |
| 12 | **Flr-B1** (F_-1_acc_Sw1) | 172.23.70.220 | SSH (port 22) | admin | secret_ref("MNE_CISCO_READONLY_CREDENTIAL") |
| 13 | **Flr-GND** (F0_acc_Sw1) | 172.23.70.221 | SSH (port 22) | admin | secret_ref("MNE_CISCO_READONLY_CREDENTIAL") |
| 14 | **Flr-1** (F1_acc_Main) | 172.23.70.222 | SSH (port 22) | admin | secret_ref("MNE_CISCO_READONLY_CREDENTIAL") |
| 15 | **Flr-2** (f2_acc_sw1) | 172.23.70.223 | SSH (port 22) | admin | secret_ref("MNE_CISCO_READONLY_CREDENTIAL") |
| 16 | **Flr-3** (f3_acc_sw1) | 172.23.70.224 | SSH (port 22) | admin | secret_ref("MNE_CISCO_READONLY_CREDENTIAL") |
| 17 | **Flr-4** (F4_acc_sw1) | 172.23.70.225 | SSH (port 22) | admin | secret_ref("MNE_CISCO_READONLY_CREDENTIAL") |
| 18 | **Flr-5** (Floor_5_main) | 172.23.70.226 | SSH (port 22) | admin | secret_ref("MNE_CISCO_READONLY_CREDENTIAL") |
| 19 | **Flr-6** (F6_acc_Sw1) | 172.23.70.227 | SSH (port 22) | admin | secret_ref("MNE_CISCO_READONLY_CREDENTIAL") |
| 20 | **Flr-Svc** (Khadamat) | 172.23.70.219 | SSH (port 22) | admin | secret_ref("MNE_CISCO_READONLY_CREDENTIAL") |

---

## 2. Windows Devices (WinRM / PowerShell)

### 2.1 Pre-Connection Setup (One-time)

Before connecting to Windows devices via WinRM, configure TrustedHosts on the local machine:

```powershell
# Run as Administrator
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "172.23.71.*" -Force
Restart-Service WinRM
```

### 2.2 Create Credential Object

```powershell
$pw = ConvertTo-SecureString $env:MNE_READONLY_SECRET -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential("MNE\admin", $pw)
```

### 2.3 Active Directory (MNE-DC1 — 172.23.71.27)

```powershell
# Connect
$s = New-PSSession -ComputerName "MNE-DC1.mne.gov" -Credential $cred -Authentication Negotiate

# Domain Info
Invoke-Command -Session $s -ScriptBlock { Get-ADDomain | Format-List * }

# Domain Controllers
Invoke-Command -Session $s -ScriptBlock { Get-ADDomainController -Filter * | Format-Table HostName, IPv4Address, OperationMasterRoles }

# User Count
Invoke-Command -Session $s -ScriptBlock { (Get-ADUser -Filter *).Count }

# Computer Count
Invoke-Command -Session $s -ScriptBlock { (Get-ADComputer -Filter *).Count }

# Group Count
Invoke-Command -Session $s -ScriptBlock { (Get-ADGroup -Filter *).Count }

# Locked-Out Users
Invoke-Command -Session $s -ScriptBlock { Search-ADAccount -LockedOut | Format-Table Name, LastLogonDate, DistinguishedName }

# Replication Health
Invoke-Command -Session $s -ScriptBlock { Get-ADReplicationPartnerMetadata -Target "mne.gov" -Scope Domain | Format-Table Server, LastReplicationAttempt, LastReplicationSuccess, ConsecutiveReplicationFailures }

# AD Health (DCDIAG)
Invoke-Command -Session $s -ScriptBlock { dcdiag /test:Advertising /test:Connectivity /test:Services /q }

# Disconnect
Remove-PSSession $s
```

### 2.4 DNS Server (MNE-DC1 — 172.23.71.27)

```powershell
$s = New-PSSession -ComputerName "MNE-DC1.mne.gov" -Credential $cred -Authentication Negotiate

# DNS Zones
Invoke-Command -Session $s -ScriptBlock { Get-DnsServerZone | Format-Table ZoneName, ZoneType, IsDsIntegrated }

# DNS Forwarders
Invoke-Command -Session $s -ScriptBlock { Get-DnsServerForwarder | Format-List IPAddress, Timeout, UseRootHint }

# DNS Statistics
Invoke-Command -Session $s -ScriptBlock { Get-DnsServerStatistics -ZoneName "mne.gov" | Format-List * }

# Test DNS Resolution
Invoke-Command -Session $s -ScriptBlock { Test-NetConnection -ComputerName "mne.gov" -InformationLevel Detailed }

# Check DNS Scavenging
Invoke-Command -Session $s -ScriptBlock { Get-DnsServerScavenging | Format-List * }

Remove-PSSession $s
```

### 2.5 Exchange Server 2019 (EXCHAMGESRV2 — 172.23.71.36)

**Step 1: Connect via WinRM to the server**
```powershell
$s = New-PSSession -ComputerName "EXCHAMGESRV2.mne.gov" -Credential $cred -Authentication Negotiate
```

**Step 2: Load Exchange cmdlets via remote PowerShell**
```powershell
Invoke-Command -Session $s -ScriptBlock {
    param($c)
    # Create Exchange-specific session
    $exSession = New-PSSession -ConfigurationName Microsoft.Exchange -ConnectionUri "http://EXCHAMGESRV2.mne.gov/PowerShell/" -Credential $c -Authentication Kerberos
    Import-PSSession $exSession -AllowClobber -DisableNameChecking | Out-Null

    # --- Exchange Commands Here ---
    Get-ExchangeServer | Format-Table Name, ServerRole, AdminDisplayVersion, Edition
    Get-MailboxDatabase | Format-Table Name, Server, Recovery, Mounted
    Get-Mailbox -ResultSize 5 | Format-Table Name, RecipientTypeDetails
    Get-DatabaseAvailabilityGroup | Format-Table Name, Servers
    Get-MailboxDatabaseCopyStatus * | Format-Table Name, Status, ContentIndexState

    # Mail Flow
    Get-Queue | Format-Table Identity, MessageCount, Status, LastError
    Get-MessageTrackingLog -ResultSize 5 -Start (Get-Date).AddHours(-1) | Format-Table Timestamp, Sender, Recipients, EventId

    Remove-PSSession $exSession
} -ArgumentList $cred

Remove-PSSession $s
```

### 2.6 Troubleshooting: Active Directory

```powershell
# Check if a user exists and is enabled
Invoke-Command -Session $s -ScriptBlock { Get-ADUser "username" -Properties Enabled, LastLogonDate, PasswordLastSet, AccountExpirationDate | Format-List }

# Check password expiry for a user
Invoke-Command -Session $s -ScriptBlock { Get-ADUserResultantPasswordPolicy "username" | Select-Object MaxPasswordAge }

# Check AD replication between DCs
Invoke-Command -Session $s -ScriptBlock { repadmin /showrepl * /csv }

# Check group membership
Invoke-Command -Session $s -ScriptBlock { Get-ADGroupMember "Group-Name" | Format-Table Name, SamAccountName, ObjectClass }

# Check recent password resets (last 24h)
Invoke-Command -Session $s -ScriptBlock {
    $yesterday = (Get-Date).AddDays(-1)
    Get-ADUser -Filter { PasswordLastSet -gt $yesterday } -Properties PasswordLastSet | Sort-Object PasswordLastSet -Descending | Format-Table Name, PasswordLastSet, Enabled
}

# Check for stale computers (not logged in for 90+ days)
Invoke-Command -Session $s -ScriptBlock {
    $cutoff = (Get-Date).AddDays(-90)
    Search-ADAccount -AccountInactive -DateTime $cutoff -ComputersOnly | Format-Table Name, LastLogonDate, Enabled
}
```

### 2.7 Troubleshooting: Exchange

```powershell
# Check database health
Invoke-Command -Session $s -ScriptBlock {
    Get-MailboxDatabase | ForEach-Object {
        Get-MailboxDatabaseCopyStatus $_.Name | Format-Table Name, Status, ContentIndexState, CopyQueueLength, ReplayQueueLength
    }
}

# Check DAG health
Invoke-Command -Session $s -ScriptBlock {
    Get-DatabaseAvailabilityGroup | ForEach-Object {
        Get-DatabaseAvailabilityGroupNetwork -Identity $_.Name | Format-Table Name, ReplicationEnabled, Subnets
    }
}

# Check mail flow issues
Invoke-Command -Session $s -ScriptBlock {
    Get-Queue | Where-Object { $_.MessageCount -gt 0 } | Format-Table Identity, MessageCount, Status, LastError
}

# Check Exchange services
Invoke-Command -Session $s -ScriptBlock {
    Get-Service -Name MSExchange* | Where-Object { $_.StartType -eq 'Automatic' } | Where-Object { $_.Status -ne 'Running' } | Format-Table Name, Status
}

# Check OWA availability
Invoke-Command -Session $s -ScriptBlock {
    Test-OwaConnectivity -MailboxCredential $using:cred | Format-Table Identity, Result, Error
}

# Check mailbox statistics
Invoke-Command -Session $s -ScriptBlock {
    Get-MailboxStatistics -Identity "user@mne.gov" | Format-Table DisplayName, TotalItemSize, ItemCount, LastLogonTime
}
```

---

## 3. Network Devices (SSH)

### 3.1 FortiGate (FGT — 172.23.70.4)

**Python/netmiko:**
```python
import netmiko
conn = netmiko.ConnectHandler(
    host='172.23.70.4',
    username='adminread',
    password = secret_ref("MNE_PLATFORM_READONLY_CREDENTIAL"),
    device_type='fortinet'
)
conn.enable()  # FGT may prompt for enable
```

**Key Read-Only Commands:**

| Category | Command | Purpose |
|----------|---------|---------|
| System | `get system status` | Version, serial, uptime, licenses |
| System | `get system performance status` | CPU, RAM, sessions, bandwidth |
| System | `get system interface physical` | Interface status and IPs |
| System | `get system arp` | ARP table |
| Routing | `get router info routing-table all` | Full routing table |
| Firewall | `get firewall policy` | All firewall policies |
| Firewall | `get firewall policy \| grep "log\|action\|hit"` | Policy hit counts |
| Log | `get log setting` | Log configuration |
| Log | `execute log filter` | Filter log entries |
| VPN | `get vpn ipsec tunnel list` | IPsec tunnel status |
| VPN | `get vpn ipsec stats tunnel` | Tunnel statistics |
| DHCP | `get dhcp server` | DHCP server config |
| DNS | `get system dns` | DNS resolver config |

**Troubleshooting Workflow:**
```bash
# Check interface status
get system interface physical

# Check routing
get router info routing-table all

# Check firewall policies with hit counts
get firewall policy

# Check active sessions
get system session list | head -50

# Check CPU and memory
get system performance status

# Check HA status (if applicable)
get system ha status

# Check VPN tunnels
get vpn ipsec tunnel list

# Check DNS resolution
execute nslookup google.com
```

---

### 3.2 Cisco FMC (172.23.70.77)

**SSH Access (requires `expert` mode for bash):**
```bash
# Login with admin/LOADED_FROM_ENV
# Shell prompt shows ">"
> expert
# Now in bash shell (prompt: admin@FMC:~$)

# Useful commands in expert mode:
cat /etc/*release          # OS info
uptime                     # System uptime
free -h                    # Memory usage
df -h                      # Disk usage
ps aux --sort=-%mem | head -10  # Top processes
ss -tlnp | head -20        # Listening services
systemctl status apache2   # Apache (FMC web) status
```

**FMC REST API (for policies and config):**
```python
import urllib.request, json, ssl, base64

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

auth = base64.b64encode(secret_ref("MNE_FMC_BASIC_AUTH")).decode()
url = 'https://172.23.70.77/api/fmc_platform/v1/auth/generatetoken'
req = urllib.request.Request(url, data=b'', method='POST')
req.add_header('Authorization', f'Basic {auth}')
req.add_header('Content-Type', 'application/json')
resp = urllib.request.urlopen(req, timeout=15, context=ctx)
token = resp.headers.get('X-auth-access-token')
domain = resp.headers.get('DOMAIN_UUID')
base = f'https://172.23.70.77/api/fmc_config/v1/domain/{domain}'

def get_json(url, tok):
    r = urllib.request.Request(url)
    r.add_header('X-auth-access-token', tok)
    return json.loads(urllib.request.urlopen(r, timeout=15, context=ctx).read().decode())

# List access policies
policies = get_json(f'{base}/policy/accesspolicies', token)

# Get rules for a specific policy
for p in policies['items']:
    rules = get_json(f'{base}/policy/accesspolicies/{p["id"]}/accessrules', token)
```

**Key API Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `GET /policy/accesspolicies` | List all access control policies |
| `GET /policy/accesspolicies/{id}/accessrules` | Get rules for a policy |
| `GET /policy/accesspolicies/{id}/defaultactions` | Get default action |
| `GET /policy/intrusionpolicies` | List IPS policies |
| `GET /device/devices/manageddevices` | List managed devices (FTD) |
| `GET /policy/ftds2svpn` | VPN policies |
| `GET /object/networks` | Network objects |
| `GET /object/securityzones` | Security zones |

**FMC Troubleshooting (expert mode):**
```bash
# Check FMC services
systemctl status ftd-mgmt  # FMC management service

# Check database health
mysql -u root -e "SHOW DATABASES;" 2>/dev/null

# Check disk space (critical for FMC)
df -h

# Check log files
tail -50 /var/log/cda/cda.log
tail -50 /var/log/sfmanager.log

# Check FMC process health
monit summary
```

---

### 3.3 Cisco FTD (172.23.70.78)

**Python/netmiko:**
```python
import netmiko
conn = netmiko.ConnectHandler(
    host='172.23.70.78',
    username='admin',
    password = secret_ref("MNE_PLATFORM_READONLY_CREDENTIAL"),
    device_type='cisco_ftd'
)
conn.enable()
```

**Key Read-Only Commands:**

| Category | Command | Purpose |
|----------|---------|---------|
| System | `show version` | FTD version, model, build |
| System | `show interface summary` | Interface status |
| System | `show inventory` | Hardware inventory |
| System | `show firewall` | Firewall mode |
| System | `show conn count` | Connection count |
| Routing | `show route` | Routing table |
| NAT | `show nat` | NAT configuration |
| NAT | `show running-config nat` | NAT rules |
| ACL | `show access-list` | Access control list with hit counts |
| ACL | `show asp drop` | Drop statistics |
| ACL | `show asp table classify domain permit \| count` | Permit rules count |
| VPN | `show vpn-sessiondb summary` | VPN sessions |
| Routing | `show route summary` | Route summary |

**Troubleshooting Workflow:**
```bash
# Check FTD mode and version
show version
show firewall

# Check interface status
show interface summary

# Check routing
show route

# Check connection counts
show conn count

# Check access rules with hit counts (find rules with 0 hits or high drops)
show access-list | include hitcnt

# Check ASP drops (why traffic is being dropped)
show asp drop

# Check Snort inspection status
show asp inspect

# Check NAT
show nat
show nat detail

# Check if Snort is blocking
show snort stats

# Check VPN sessions
show vpn-sessiondb summary
```

**FMC API for FTD policies:**
The FTD is managed by FMC. Most policy changes must be done via the FMC REST API (see section 4).

---

### 3.4 F5 BIG-IP (172.23.70.89)

**Python/netmiko:**
```python
import netmiko
conn = netmiko.ConnectHandler(
    host='172.23.70.89',
    username='admin',
    password = secret_ref("MNE_PLATFORM_READONLY_CREDENTIAL"),
    device_type='f5_ltm'
)
```

**Key Read-Only Commands (tmsh):**

| Category | Command | Purpose |
|----------|---------|---------|
| System | `show sys version` | F5 version |
| System | `show sys hardware` | Hardware info |
| System | `show sys performance` | CPU, memory, connections |
| Network | `show net interface` | Interface status |
| Network | `show net route` | Routing table |
| Network | `show net routing self` | Self-IPs |
| LTM | `show ltm virtual` | Virtual servers |
| LTM | `show ltm pool` | Pools |
| LTM | `show ltm node` | Nodes (servers) |
| LTM | `show ltm monitor` | Monitors |
| Security | `show security firewall` | Firewall rules |
| DNS | `show gtm` | DNS/GTM config |
| Logging | `show ltm monitor` | Health monitors |

**Troubleshooting Workflow:**
```bash
# Check version and system health
show sys version
show sys hardware
show sys performance

# Check interfaces
show net interface

# Check virtual servers and pools
show ltm virtual
show ltm pool
show ltm node

# Check routing
show net route
show net routing self

# Check connections to a specific VIP
show ltm virtual AGENCY-VS

# Check pool member health
show ltm pool APDCT_Pool members

# Check logs
show ltm monitor

# Check iRules
show ltm rule
```

---

### 3.5 Cisco Core Switch (CoreSwitch1 — 172.23.70.254)

**Python/netmiko:**
```python
import netmiko
conn = netmiko.ConnectHandler(
    host='172.23.70.254',
    username='admin',
    password = secret_ref("MNE_PLATFORM_READONLY_CREDENTIAL"),
    device_type='cisco_ios',
    fast_cli=False
)
# Note: Enable password required for privileged mode.
# Currently limited to user exec mode (CoreSwitch1>)
```

**Interactive SSH (user exec):**
```python
import paramiko, time
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.23.70.254', username='admin', password = secret_ref("MNE_PLATFORM_READONLY_CREDENTIAL"), timeout=15, look_for_keys=False, allow_agent=False)
channel = client.invoke_shell(width=200, height=50)
time.sleep(2)
channel.recv(4096)
channel.send('show version\n')
time.sleep(3)
data = channel.recv(8192).decode()
```

**Key Read-Only Commands (User Exec Mode):**

| Category | Command | Purpose |
|----------|---------|---------|
| System | `show version` | IOS version, uptime, model |
| VLAN | `show vlan brief` | VLAN list |
| Interface | `show interfaces status` | Port status |
| Interface | `show ip interface brief` | Interface IP summary |
| Routing | `show ip route` | Routing table |
| CDP | `show cdp neighbors` | Connected devices |
| STP | `show spanning-tree` | Spanning tree status |
| ARP | `show arp` | ARP table |

**Troubleshooting Workflow:**
```bash
show version
show vlan brief
show interfaces status
show ip interface brief
show ip route
show cdp neighbors
show spanning-tree
show arp
show logging | include error
show interfaces | include drops|errors
show mac address-table
```

---

### 3.6 Fujitsu PSWITCH 2048P (SW1 — 172.23.70.70, SW2 — 172.23.70.71)

**Python/netmiko:**
```python
import netmiko
conn = netmiko.ConnectHandler(
    host='172.23.70.70',  # or 172.23.70.71 for SW2
    username='admin',
    password = secret_ref("MNE_PLATFORM_READONLY_CREDENTIAL"),
    device_type='cisco_ios'  # Fujitsu uses Cisco-like CLI
)
conn.enable()
```

**Key Read-Only Commands:**

| Category | Command | Purpose |
|----------|---------|---------|
| System | `show version` | Firmware version |
| System | `show hardware` | Model, serial, MAC |
| System | `show environment` | Temperature, fans, PSU |
| VLAN | `show vlan brief` | VLAN list |
| MAC | `show mac-addr-table` | MAC address table |
| STP | `show spanning-tree` | Spanning tree status |
| Routing | `show ip route` | Routing table |
| Routing | `show ip interface brief` | L3 interface summary |
| LAG | `show port-channel brief` | LACP/LAG status |
| LLDP | `show lldp neighbors` | Neighbor discovery |
| Config | `show running-config` | Running configuration |
| Config | `show startup-config` | Saved configuration |

**Troubleshooting Workflow:**
```bash
# System health
show version
show hardware
show environment

# VLAN and MAC table
show vlan brief
show mac-addr-table

# Spanning tree (check for topology changes)
show spanning-tree

# Interface status
show interfaces

# Routing
show ip route
show ip interface brief

# LACP/LAG
show port-channel brief
show lacp summary

# LLDP neighbors
show lldp neighbors

# Running config
show running-config
```

---

### 3.7 vCenter (VCSA 7.0.3 — 172.23.69.38)

**SSH Access (requires `shell` to enter bash):**
```python
import paramiko, time
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.23.69.38', username='root', password = secret_ref("MNE_PLATFORM_READONLY_CREDENTIAL"), timeout=15, look_for_keys=False, allow_agent=False)
channel = client.invoke_shell(width=200, height=50)
time.sleep(2)
channel.recv(4096)
channel.send('shell\n')
time.sleep(3)
channel.recv(8192)
# Now in bash shell

# Useful commands
channel.send('hostname\n')
channel.send('uptime\n')
channel.send('free -h\n')
channel.send('df -h\n')
channel.send('vmon-cli -l\n')
channel.send('service-control --status\n')
```

**Key Read-Only Commands:**

| Category | Command | Purpose |
|----------|---------|---------|
| System | `hostname` | Host name |
| System | `uptime` | System uptime |
| System | `free -h` | Memory usage |
| System | `df -h` | Disk usage |
| Version | `vpxd -v` | vCenter version |
| Services | `vmon-cli -l` | List all services |
| Services | `service-control --status` | Service status |
| Database | `cat /etc/vmware-vpx/vcdb.properties` | DB connection info |
| Logs | `cat /var/log/vmware/vpxd/vpxd.log \| tail -50` | vCenter logs |
| Backup | `cat /etc/appliances-version.xml` | Appliance version |

**Troubleshooting Workflow:**
```bash
# Enter shell
shell

# System health
uptime
free -h
df -h / /storage/log /storage/db /storage/archive

# Check services
service-control --status

# Check vCenter version
vpxd -v

# Check logs (if vCenter has issues)
tail -100 /var/log/vmware/vpxd/vpxd.log | grep -i error

# Check database connectivity
cat /etc/vmware-vpx/vcdb.properties

# Check storage health
vdcs -c check --all
```

---

### 3.8 Floor Switches (Cisco Catalyst 9K Lite)

All floor switches are Cisco Catalyst 9K Lite (CAT9K_LITE_IOSXE) running IOS XE 17.x. They share the same credentials and command set.

| Name | Hostname | IP | IOS XE | Connected Ports |
|------|----------|-----|--------|----------------|
| Flr-B1 | F_-1_acc_Sw1 | 172.23.70.220 | 17.12.4 | 21 |
| Flr-GND | F0_acc_Sw1 | 172.23.70.221 | 17.15.3 | 16 |
| Flr-1 | F1_acc_Main | 172.23.70.222 | 17.15.3 | 29 |
| Flr-2 | f2_acc_sw1 | 172.23.70.223 | 17.12.4 | 28 |
| Flr-3 | f3_acc_sw1 | 172.23.70.224 | 17.12.4 | 26 |
| Flr-4 | F4_acc_sw1 | 172.23.70.225 | 17.12.4 | 31 |
| Flr-5 | Floor_5_main | 172.23.70.226 | 17.12.4 | 20 |
| Flr-6 | F6_acc_Sw1 | 172.23.70.227 | 17.12.4 | 24 |
| Flr-Svc | Khadamat | 172.23.70.219 | 17.12.3 | 15 |

**Python/netmiko (user exec mode):**
```python
import netmiko
conn = netmiko.ConnectHandler(
    host='172.23.70.220',  # change IP per switch
    username='admin',
    password = secret_ref("MNE_PLATFORM_READONLY_CREDENTIAL"),
    device_type='cisco_ios',
    fast_cli=False
)
# Note: May require enable password for privileged mode.
# Currently tested in user exec mode.
```

**Interactive SSH:**
```python
import paramiko, time
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('172.23.70.220', username='admin', password = secret_ref("MNE_PLATFORM_READONLY_CREDENTIAL"), timeout=10, look_for_keys=False, allow_agent=False)
channel = client.invoke_shell(width=200, height=50)
time.sleep(2)
channel.recv(4096)
channel.send('show version\n')
time.sleep(3)
data = channel.recv(8192).decode()
```

**Key Read-Only Commands:**

| Category | Command | Purpose |
|----------|---------|---------|
| System | `show version` | IOS version, uptime, model |
| VLAN | `show vlan brief` | VLAN list |
| Interface | `show interfaces status` | Port status |
| Interface | `show ip interface brief` | Interface IP summary |
| Routing | `show ip route` | Routing table |
| CDP | `show cdp neighbors` | Connected devices |
| STP | `show spanning-tree` | Spanning tree status |
| ARP | `show arp` | ARP table |
| MAC | `show mac address-table` | MAC address table |

**Troubleshooting Workflow:**
```bash
show version
show vlan brief
show interfaces status
show ip interface brief
show cdp neighbors
show spanning-tree
show mac address-table
show interfaces | include errors|drops
```

---

## 4. FMC API (for policies)

The FMC REST API is the programmatic way to read all FTD/FTD policies, objects, and device settings.

### 4.1 Authentication

```python
import urllib.request, json, ssl, base64

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

auth = base64.b64encode(secret_ref("MNE_FMC_BASIC_AUTH")).decode()
url = 'https://172.23.70.77/api/fmc_platform/v1/auth/generatetoken'
req = urllib.request.Request(url, data=b'', method='POST')
req.add_header('Authorization', f'Basic {auth}')
req.add_header('Content-Type', 'application/json')
resp = urllib.request.urlopen(req, timeout=15, context=ctx)
token = resp.headers.get('X-auth-access-token')
domain = resp.headers.get('DOMAIN_UUID')
base = f'https://172.23.70.77/api/fmc_config/v1/domain/{domain}'

def get_json(url, tok):
    r = urllib.request.Request(url)
    r.add_header('X-auth-access-token', tok)
    return json.loads(urllib.request.urlopen(r, timeout=15, context=ctx).read().decode())
```

### 4.2 Key API Endpoints

| Category | Endpoint | Purpose |
|----------|----------|---------|
| Policies | `GET /policy/accesspolicies` | List all access policies |
| Policies | `GET /policy/accesspolicies/{id}/accessrules` | Get rules for a policy |
| Policies | `GET /policy/accesspolicies/{id}/defaultactions` | Get default action |
| Devices | `GET /device/devices/manageddevices` | List managed FTDs |
| Objects | `GET /object/networks` | Network objects |
| Objects | `GET /object/securityzones` | Security zones |
| Objects | `GET /object/ports` | Port/service objects |
| IPS | `GET /policy/intrusionpolicies` | IPS policies |
| VPN | `GET /policy/ftds2svpn` | Site-to-site VPN |
| NAT | `GET /policy/accesspolicies/{id}/autonatrules` | NAT rules |

### 4.3 Action Codes

| Code | Meaning |
|------|---------|
| 0 | PERMIT |
| 1 | TRUST |
| 2 | MONITOR |
| 3 | BLOCK |
| 4 | BLOCK_RESET |
| 5 | BLOCK_INTERACTIVE |
| 6 | BLOCK_QUICK |

---

## 5. General Troubleshooting Workflows

### 5.1 Network Connectivity Issue

```
1. Check interface status on source device
   - FTD: show interface summary
   - FGT: get system interface physical
   - Core: show interfaces status
   - Fujitsu: show interfaces

2. Check routing
   - FTD: show route
   - FGT: get router info routing-table all
   - Core: show ip route
   - Fujitsu: show ip route

3. Check ARP resolution
   - FTD: show arp
   - FGT: get system arp
   - Core: show arp
   - Fujitsu: show arp (via show running-config)

4. Check firewall rules
   - FTD: show access-list (check hit counts)
   - FGT: get firewall policy (check hit counts)
   - F5: show ltm virtual (check pool member health)

5. Check FMC policy default action
   - FMC API: GET /policy/accesspolicies/{id}/defaultactions
   - If "PERMIT" → all traffic passes by default
   - If "BLOCK" → only explicitly allowed traffic passes

6. Check DNS resolution
   - Windows DC: Resolve-DnsName <target>
   - FGT: execute nslookup <target>
   - FMC (expert): nslookup <target>
```

### 5.2 Service Not Responding

```
1. Check service status
   - Windows: Get-Service -Name <service>
   - Exchange: Get-Service -Name MSExchange*
   - FMC (expert): systemctl status <service>
   - vCenter: service-control --status

2. Check port availability
   - Test-NetConnection -Port <port> -ComputerName <target>

3. Check disk space
   - Windows: Get-PSDrive -PSProvider FileSystem
   - FMC (expert): df -h
   - vCenter: df -h /storage/*
   - F5: show sys hardware

4. Check memory
   - Windows: Get-CimInstance Win32_OperatingSystem
   - Linux/Unix: free -h
   - F5: show sys performance

5. Check logs
   - Windows: Get-EventLog -LogName System -Newest 50
   - Exchange: Get-MessageTrackingLog
   - FMC (expert): tail -50 /var/log/sfmanager.log
   - vCenter: tail -50 /var/log/vmware/vpxd/vpxd.log
```

### 5.3 DNS Resolution Issue

```
1. Check DNS server health (on MNE-DC1)
   - Get-DnsServerZone
   - Get-DnsServerForwarder
   - Test-NetConnection -Port 53 -ComputerName <target>

2. Check AD/DNS replication
   - repadmin /showrepl * /csv
   - Get-ADReplicationPartnerMetadata

3. Check DNS forwarders
   - Get-DnsServerForwarder | Format-List IPAddress

4. Check DNS zones
   - Get-DnsServerZone | Where-Object { $_.ZoneType -eq 'Primary' }

5. Test from multiple sources
   - Windows DC: Resolve-DnsName <target>
   - FGT: execute nslookup <target>
   - FMC (expert): nslookup <target>
```

### 5.4 Exchange Mail Flow Issue

```
1. Check queue status
   - Get-Queue | Where-Object { $_.MessageCount -gt 0 }

2. Check database status
   - Get-MailboxDatabaseCopyStatus *

3. Check DAG health
   - Get-DatabaseAvailabilityGroup

4. Check mail flow logs
   - Get-MessageTrackingLog -Start (Get-Date).AddHours(-24) | Where-Object { $_.EventId -eq 'FAIL' }

5. Check Exchange services
   - Get-Service -Name MSExchange* | Where-Object { $_.Status -ne 'Running' }

6. Check receive connectors
   - Get-ReceiveConnector | Format-Table Name, Bindings, Enabled

7. Check send connectors
   - Get-SendConnector | Format-Table Name, AddressSpaces
```

---

## 6. Common Issues & Commands

### 6.1 Known Flags in the Infrastructure

| Issue | Device | Severity | Details |
|-------|--------|----------|---------|
| **FMC Default Action = PERMIT** | FMC/FTD | 🔴 Critical | All traffic passes by default. Change to BLOCK |
| **IPS in DETECTION mode** | FMC/FTD | 🟡 Medium | Snort inspects but doesn't block. Change to PREVENTION |
| **SW2 STP flapping** | Fuj-SW2 | 🟡 Medium | 107K topology changes vs SW1's 3. Check `show spanning-tree` |
| **VCenter archive 95% full** | VCenter | 🟡 Medium | /storage/archive at 89GB/98GB. Clean up or expand |
| **Exchange system mailbox corruption** | Exchange | 🟡 Medium | 3 arbitration mailboxes with DB validation errors |
| **Cisco enable password missing** | Cisco-Core | ⚪ Low | Only user exec mode available |

### 6.2 Quick Health Check Commands

```bash
# FortiGate
get system performance status
get system session list | wc -l

# FTD (via FMC API)
# Check default action

# F5
show ltm virtual | grep "available\|disabled"
show ltm pool | grep "available\|offline"

# Fujitsu SW1
show spanning-tree | grep "Topology Change"
show environment | grep "Fan\|Temp"

# Fujitsu SW2
show spanning-tree | grep "Topology Change"

# Cisco Core
show interfaces | include drops|errors

# vCenter
service-control --status | grep "Stopped"

# Active Directory
Get-ADReplicationPartnerMetadata -Target "mne.gov" -Scope Domain

# Exchange
Get-MailboxDatabaseCopyStatus * | Where-Object { $_.Status -ne "Mounted" -or $_.ContentIndexState -ne "Healthy" }
```

### 6.3 Session Management

When connecting from Python:
```python
# Always disconnect when done
conn.disconnect()

# For WinRM:
Remove-PSSession $s

# For paramiko:
client.close()

# For FMC API:
# Tokens expire after 30 minutes; re-authenticate if needed
```

---

## 8. Device Summary

```
Internet (213.6.17.29)
    │
    ▼
┌─────────────┐
│  FortiGate  │ 172.23.70.4 — Gateway, NAT, routing
│  FG-401F    │ v7.4.11, 16GB RAM, ~11K sessions
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Cisco Core     │ 172.23.70.254 — Core switch, Cat9K stack
│  CoreSwitch1    │ IOS-XE 17.9.6a, SVI: Vlan9/70/1011
└──────┬──────────┘
       │
       ├── Fuj-SW1 (172.23.70.70) — FW 1.3.68, ET-7648BFRA-FOS
       │   ├── Fuj-SW2 (172.23.70.71) — FW 1.3.67, ET-7648BFRA-FOS
       │   │   ├── AD + DNS (172.23.71.27) — WS2019, 2 DCs
       │   │   ├── Exchange (172.23.71.36) — 2019 Ent, 2-server DAG
       │   │   ├── FMC (172.23.70.77) — v7.7.0, manages FTD
       │   │   ├── FTD (172.23.70.78) — v7.6.2, internal firewall
       │   │   ├── F5 (172.23.70.89) — v17.5.1.3, load balancer
       │   │   └── vCenter (172.23.69.38) — VCSA 7.0.3, manages VMs
       │   │
       │   └── (All 30 VLANs trunked)
       │
       ├── Floor Switches (Cat9K Lite, IOS-XE 17.x):
       │   ├── Flr-B1    (F_-1_acc_Sw1)  172.23.70.220  21 ports up
       │   ├── Flr-GND   (F0_acc_Sw1)    172.23.70.221  16 ports up
       │   ├── Flr-1     (F1_acc_Main)   172.23.70.222  29 ports up
       │   ├── Flr-2     (f2_acc_sw1)    172.23.70.223  28 ports up
       │   ├── Flr-3     (f3_acc_sw1)    172.23.70.224  26 ports up
       │   ├── Flr-4     (F4_acc_sw1)    172.23.70.225  31 ports up
       │   ├── Flr-5     (Floor_5_main)  172.23.70.226  20 ports up
       │   ├── Flr-6     (F6_acc_Sw1)    172.23.70.227  24 ports up
       │   └── Flr-Svc   (Khadamat)      172.23.70.219  15 ports up
       │
       └── Server segments:
           ├── 172.23.69.0/24 (Server-Mgmt)
           ├── 172.23.70.0/24 (Management)
           ├── 172.23.71.0/24 (Servers)
           └── 172.23.72-88.0/24 (Various server subnets)
```
