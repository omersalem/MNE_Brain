# GUI — Cockpit Web Console
## Ubuntu Server 24.04 — Full GUI Reference

---

## WHAT IS COCKPIT?

Cockpit is the official web-based GUI for Ubuntu Server administration.
It provides a browser-based interface to manage the server without memorizing CLI commands.

```
URL:      https://SERVER-IP:9090
Protocol: HTTPS (self-signed cert by default)
Auth:     Same as Linux system users (sudo user for admin tasks)
Port:     9090 (TCP)
```

---

## INSTALLATION & SETUP

```bash
# Install Cockpit
sudo apt install cockpit

# Enable and start
sudo systemctl enable --now cockpit.socket

# Open firewall
sudo ufw allow 9090/tcp comment 'Cockpit Web GUI'

# Verify
systemctl status cockpit.socket
ss -lntp | grep 9090

# Access: https://SERVER-IP:9090
# Accept self-signed certificate warning in browser
# Login with: your Linux username + password
```

### Cockpit Modules (Additional Features)

```bash
# Install additional Cockpit modules
sudo apt install cockpit-machines          # Virtual Machine management (KVM/libvirt)
sudo apt install cockpit-docker            # Docker container management
sudo apt install cockpit-storaged          # Advanced storage management
sudo apt install cockpit-packagekit        # GUI package management
sudo apt install cockpit-networkmanager    # NetworkManager integration
sudo apt install cockpit-podman            # Podman containers
sudo apt install cockpit-sosreport         # Support case tool
sudo apt install cockpit-pcp               # Performance metrics (PCP)

# After installing modules, reload Cockpit:
sudo systemctl restart cockpit.socket
```

---

## COCKPIT NAVIGATION

```
Left Sidebar Menu:
  ├── Overview           ← System health at a glance
  ├── Logs               ← System journal (journalctl GUI)
  ├── Storage            ← Disks, filesystems, LVM, RAID
  ├── Networking         ← Network interfaces, routes, firewall
  ├── Accounts           ← Users and groups management
  ├── Services           ← systemd service management
  ├── Applications       ← Cockpit module apps
  ├── Software Updates   ← APT package updates
  ├── Terminal           ← Built-in web terminal
  └── [Additional panels if modules installed]
      ├── Virtual Machines (cockpit-machines)
      ├── Podman Containers (cockpit-podman)
      └── Performance Metrics (cockpit-pcp)
```

---

## OVERVIEW PANEL

```
Location: Cockpit → Overview (homepage)

What you see:
  ┌─────────────────────────────────────────────────┐
  │ System Info                                     │
  │   Hostname: myserver                            │
  │   Operating system: Ubuntu 24.04 LTS            │
  │   Kernel: 6.8.0-xx-generic                     │
  │   CPU: Intel Core i5 @ 3.4GHz (4 cores)        │
  │   Memory: 8 GB                                  │
  │   Uptime: 5 days, 3 hours                       │
  ├─────────────────────────────────────────────────┤
  │ Health                                          │
  │   ● Running processes: 142                      │
  │   ● Disk I/O: Normal                            │
  │   ● CPU Load: 12%                               │
  │   ● Memory: 3.2 GB / 8 GB                      │
  ├─────────────────────────────────────────────────┤
  │ Performance Graphs                              │
  │   CPU: [live graph]                             │
  │   Memory: [live graph]                          │
  │   Disk I/O: [live graph]                        │
  │   Network: [live graph]                         │
  └─────────────────────────────────────────────────┘

Actions available:
  → Hostname: click to edit
  → System time: click to configure NTP
  → Restart/Shutdown button (top right)
  → Join Domain button (if available)
```

---

## LOGS PANEL

```
Location: Cockpit → Logs

Features:
  - Real-time log streaming (live view)
  - Filter by: Time period, Priority, Service name, Search text
  
  Priority filters:
    ● Emergency + Alert + Critical + Error  (red — most important)
    ○ Warning
    ○ Notice + Info
    ○ Debug

  Time filters:
    ● Last Hour  ● Last 24 Hours  ● Last Week  ● Custom range

  Service filter: type service name (e.g., "nginx", "ssh", "ufw")
  
  Text search: type any keyword to search log messages

  Each log entry shows:
    - Timestamp
    - Hostname
    - Service name (click to filter by this service)
    - Message
    - Priority color indicator

  Click any log entry → expand to see full details
```

---

## STORAGE PANEL

```
Location: Cockpit → Storage

Main view shows:
  ┌─────────────────────────────────────────────────┐
  │ Storage Summary                                 │
  │   I/O speed: Read 45 MB/s  Write 12 MB/s       │
  ├─────────────────────────────────────────────────┤
  │ Filesystems                                     │
  │   / (root)    ext4    50 GB / 100 GB used       │
  │   /boot       ext4    800 MB / 1 GB             │
  │   /home       ext4    35 GB / 200 GB            │
  │   [click any row to see details + actions]      │
  ├─────────────────────────────────────────────────┤
  │ Drives                                          │
  │   sda    Samsung SSD 870    500 GB              │
  │   sdb    WD Blue HDD        2 TB                │
  │   [click to see partition table + SMART]        │
  ├─────────────────────────────────────────────────┤
  │ VDO Devices / RAID / LVM Volume Groups          │
  └─────────────────────────────────────────────────┘

Actions:
  → Click a drive → view partitions, create/delete partitions
  → Click a filesystem → see mount point, usage, unmount, format
  → "+" button → Create new filesystem, RAID, VDO, or LVM group

LVM Management:
  Cockpit → Storage → click Volume Group
    → Create Logical Volume
    → Grow / Shrink LV
    → Create snapshot
    → Deactivate / Delete
```

---

## NETWORKING PANEL

```
Location: Cockpit → Networking

Main view:
  ┌─────────────────────────────────────────────────┐
  │ Firewall                                        │
  │   Status: Active  [Edit rules...]               │
  ├─────────────────────────────────────────────────┤
  │ Interfaces                                      │
  │   enp0s3   192.168.1.100/24   1Gbps   ● UP     │
  │   enp0s8   10.0.0.10/24      1Gbps   ● UP      │
  │   lo        127.0.0.1/8               ● UP     │
  ├─────────────────────────────────────────────────┤
  │ Network graph                                   │
  │   Sending: 2.3 MB/s  Receiving: 1.1 MB/s       │
  └─────────────────────────────────────────────────┘

Interface actions (click interface):
  → View current IP, gateway, DNS
  → Edit IPv4/IPv6 settings (static/DHCP)
  → Manage DNS servers
  → Add/remove routes
  → Delete interface

Firewall management:
  Cockpit → Networking → Firewall → Edit Rules
    → Add rule: Port/Service + Allow/Deny
    → Delete rule
    → View active rules

Create new connections:
  "+" button → Bond / Bridge / VLAN / Team
```

---

## ACCOUNTS PANEL

```
Location: Cockpit → Accounts

Main view shows:
  - All system users with: username, full name, last login, admin status
  - Locked accounts shown with lock icon

Create new user:
  "+" button → Create New Account
    Full name: John Smith
    User name: jsmith
    Password: [set or leave for SSH key only]
    
User details (click any user):
  → Change password
  → Force password change on next login
  → Lock/unlock account
  → Delete account
  → Assign administrator role (adds to sudo group)
  → Add SSH public keys (paste public key)
  → View last login info

Roles:
  Administrator = member of sudo group
  Standard user = no sudo
```

---

## SERVICES PANEL

```
Location: Cockpit → Services

View:
  Tabs: System Services | Sockets | Timers | Paths | Targets
  
  Filter by: Running | Enabled | Disabled | Static
  Search bar: type service name

  Each service shows:
    ● green dot = running
    ○ grey dot = stopped
    ✗ red dot = failed
    Name | Description | State | Auto-start

Actions (click any service → Details panel):
  → Start / Stop / Restart
  → Enable / Disable (auto-start on boot)
  → Reload (if service supports it)
  → View live logs for this service
  → View service file (unit file contents)

Creating service units:
  Not available in Cockpit GUI — use terminal or drop unit file manually
```

---

## SOFTWARE UPDATES PANEL

```
Location: Cockpit → Software Updates
(Requires: cockpit-packagekit package)

Features:
  - List all available updates
  - Show security updates separately (highlighted)
  - Apply updates with one click
  - View update history

Actions:
  → "Check for Updates" button
  → "Install All Updates" button
  → Select individual packages to update
  → Schedule automatic updates
  → View changelog for each update
```

---

## TERMINAL PANEL

```
Location: Cockpit → Terminal

Full web-based terminal — same as SSH session
  - Color output
  - Ctrl+C, Ctrl+D work normally
  - Copy/paste: Ctrl+Shift+C / Ctrl+Shift+V
  - Can run sudo commands (prompts for password)
  - Session persists while browser tab is open

Useful when:
  - SSH client not available
  - Need GUI + terminal together
  - Remote access via browser only
```

---

## VIRTUAL MACHINES PANEL (cockpit-machines)

```
Location: Cockpit → Virtual Machines
(Requires: cockpit-machines + libvirt-daemon)

sudo apt install cockpit-machines libvirt-daemon-system
sudo usermod -aG libvirt $USER

Features:
  - Create new VMs from ISO or cloud image
  - Start / Stop / Suspend / Resume VMs
  - View VM console (VNC/SPICE in browser)
  - Manage virtual networks and storage pools
  - Edit VM resources (CPU, RAM, disk)
  - Clone VMs
  - Take snapshots

Create VM:
  → Create VM → 
    Name, installation source (ISO/URL),
    Storage (size + pool),
    Memory, CPU count
  → Install
  → Opens console in browser for installation

VM Actions:
  Click VM → 
    Run / Shut down / Force off / Restart
    Console (open graphical console)
    Edit settings (disk, network, CPU, memory)
    Delete
```

---

## COCKPIT SECURITY

```bash
# Allow only specific users to use Cockpit
# /etc/cockpit/cockpit.conf
[WebService]
AllowUnencrypted = false

# Restrict by user (add to PAM or group):
# Only users in cockpit-users group can log in:
sudo groupadd cockpit-users
sudo usermod -aG cockpit-users jsmith

# Add to /etc/pam.d/cockpit:
account required pam_access.so
# And /etc/security/access.conf:
+ : (cockpit-users) : ALL
- : ALL : ALL

# Change Cockpit port:
# /etc/cockpit/cockpit.conf
[WebService]
Origins = https://myserver:9090
# Then update socket: systemctl restart cockpit.socket

# Disable Cockpit (when not needed):
sudo systemctl stop cockpit.socket
sudo systemctl disable cockpit.socket
sudo ufw delete allow 9090/tcp
```
