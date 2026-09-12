# FortiEDR 6.2 — Authoritative CLI & Collector Deployment Reference Guide

> **Organization:** `MNE`  
> **Console Domain:** `fortiedrconnectil.console.ensilo.com`  
> **Software Release:** FortiEDR 6.2  
> **Source Attribution:** Fortinet FortiEDR 6.2 Administration Guide (Doc ID: 354083 / CLI Guide 671625)  
> **Classification:** Engineering Operational Reference (Single Source of Truth)  

---

## 🛠️ 1. Server Appliance CLI Utility (`fortiedr`)

The `fortiedr` command-line interface utility is installed on all backend infrastructure components (FortiEDR Central Manager, Aggregator, Core, Threat Hunting Repository Server, and ActiveMQ broker).

### Basic Syntax:
```bash
fortiedr <action>
fortiedr <component> <action> [options]
```

### 1.1 Basic System Actions:
| Command | Description |
| :--- | :--- |
| `fortiedr help` | Displays full list of available commands and usage instructions. |
| `fortiedr config` | Runs the interactive FortiEDR installation and initial setup wizard. |
| `fortiedr start` | Starts all active FortiEDR services on the appliance. |
| `fortiedr stop` | Gracefully stops all FortiEDR services. |
| `fortiedr status` | Queries and prints the operational status of all local services. |
| `fortiedr version` | Outputs the installed build and component versions (e.g. `6.2.0.x`). |
| `fortiedr tzselect` | Interactive timezone selection utility for appliance clock sync. |
| `fortiedr logs-watch` | Tails live logging streams for Aggregator and Central Manager. |

### 1.2 General Service Control Grammar:
To control specific underlying daemons:
```bash
fortiedr {edr|aggregator|core|manager|activemq} {start|stop|restart|status|enable|disable}
```
- `edr`: Core detection engine daemon.
- `aggregator`: Collector communication and proxy daemon.
- `core`: Real-time prevention and behavioral evaluation service.
- `manager`: Web console and Central Manager application server.
- `activemq`: Message bus coordinator for distributed tasks.

---

### 1.3 Component-Specific CLI Commands:

#### A. FortiEDR Aggregator Controls:
```bash
# Start Aggregator in verbose debug mode
fortiedr aggregator start-debug

# Stop debug mode and return to standard logging
fortiedr aggregator stop-debug

# Change the TCP port on which Aggregator listens for Collector connections (Default: 8081)
fortiedr aggregator port-change <port>

# Set or update the Aggregator external DNS hostname
fortiedr aggregator set-dns <dns_name>

# Configure Aggregator bandwidth limit in Kb/s (useful for remote WAN branches)
fortiedr aggregator bandwidth config <bandwidth>

# Enable bandwidth throttling
fortiedr aggregator bandwidth enable

# Disable bandwidth throttling
fortiedr aggregator bandwidth disable

# Tail Aggregator diagnostic logs
fortiedr aggregator logs-watch
```

#### B. ActiveMQ Message Broker Controls:
```bash
# Display detailed metrics and message counts for internal messaging queues
fortiedr activemq queue-stat [<queue_name>]
```

#### C. FortiEDR Core & EDR Engine Controls:
```bash
# Set administrative authentication credentials
fortiedr edr set-properties <username> '<password>'

# Run EDR Core engine in debug mode
fortiedr edr start-debug

# Stop EDR Core debug mode
fortiedr edr stop-debug
```

#### D. FortiEDR Central Manager (Console) Controls:
```bash
# Run Central Manager in debug mode
fortiedr manager start-debug
fortiedr manager stop-debug

# Reset web password for a specific console user
fortiedr manager reset-password <username>

# Load new dynamic security content package
fortiedr manager load-content <password>

# Load extra configuration overrides
fortiedr manager load-extra-config <password>

# Install custom SSL/TLS certificate for web console
fortiedr manager load-ssl-certificate <user> <password> <cert_path> <key_path> <key_password>

# Configure SMTP relay server IP in application-customer.properties
fortiedr manager set-smtp-server <ip_address>

# Link Central Manager to Core EDR server IP and port
fortiedr manager set-edr-ip <ip>:<port>
fortiedr manager set-edr-user <username>
fortiedr manager set-edr-password <password>

# Enable or disable EDR subsystem inside Central Manager
fortiedr manager enable-edr
fortiedr manager disable-edr

# Tail Central Manager live application logs
fortiedr manager logs-watch
```

---

## 💻 2. Endpoint Collector Deployment & Command-Line Operations

FortiEDR Collectors run on enterprise endpoints. They require zero local configuration files and register dynamically with the cloud tenant.

### 2.1 Windows Collector Silent Installation

#### Customized Installer (Recommended):
When downloaded directly from the Central Manager console, the installer has the Aggregator address and registration password embedded:
```powershell
msiexec /i FortiEDRCollectorInstaller64.msi /qn
```

#### Non-Customized (Generic) MSI Silent Installation:
When deploying generic installation packages across the MNE network:
```powershell
msiexec /i FortiEDRCollectorInstaller64.msi /qn `
  AGG=fortiedrconnectil.console.ensilo.com:8081 `
  PWD=<RegistrationPassword> `
  ORG="MNE" `
  DEFGROUP="Default Collector Group"
```

#### Full Parameter Reference for Windows:
| Parameter | Required | Description | Example |
| :--- | :--- | :--- | :--- |
| `AGG` | Yes (Generic) | FQDN or IP of Aggregator with port `8081` | `AGG=fortiedrconnectil.console.ensilo.com:8081` |
| `PWD` | Yes (Generic) | Device registration password defined in Central Manager | `PWD=RegistrationSecret` |
| `ORG` | Yes (Multi-tenant) | Organization name in quotes | `ORG="MNE"` |
| `DEFGROUP` | Optional | Initial Collector Group assignment | `DEFGROUP="Workstations"` |
| `PROXY=1` | Optional | Forces agent to use Windows system WinHTTP proxy | `PROXY=1` |
| `NEEDREBOOT=1`| Optional | Marks device as Pending Reboot; engages hooks only post-reboot | `NEEDREBOOT=1` |
| `CITRIXPVS=1` | Optional | Configures agent for Citrix PVS / non-persistent VDI golden image | `CITRIXPVS=1` |

#### Windows Service Verification & Health Checks:
```powershell
# Verify FortiEDR Windows Service is running
Get-Service -Name FortiEDRCollectorService

# Service query via sc.exe
sc.exe query FortiEDRCollectorService

# Check running driver filter hooks
fltmc.exe instances | Select-String "ensilo|fortiedr"
```

---

### 2.2 Linux Collector Silent Installation

Supported Distributions: RHEL/CentOS 7/8/9, Ubuntu 18.04/20.04/22.04, SUSE Linux Enterprise 12/15, Oracle Linux.

#### Package Installation Commands:
```bash
# RHEL / CentOS / Oracle Linux (RPM):
sudo yum install -y ./FortiEDRCollectorInstaller_CentOS8-6.2.0-xx.x86_64.rpm

# Ubuntu / Debian (DEB):
sudo apt-get install -y ./FortiEDRCollectorInstaller_Ubuntu-6.2.0-xx.deb

# SUSE Linux (Zypper):
sudo rpm --import RPM-GPG-KEY.key
sudo zypper install -y ./FortiEDRCollectorInstaller_openSUSE15-6.2.0-xx.rpm
```

#### Post-Installation Configuration Script (`fortiedrconfig.sh`):
After package installation, run the registration script:
```bash
sudo /opt/FortiEDRCollector/scripts/fortiedrconfig.sh
```
Prompts and inputs required:
1. **Aggregator Address & Port:** `fortiedrconnectil.console.ensilo.com:8081`
2. **Organization Name:** `MNE`
3. **Collector Group:** `Default Collector Group` (or specific group name)
4. **Registration Password:** `<RegistrationPassword>`
5. **Proxy Configuration:** `Y` or `N`
6. **Kernel Module Signing (Secure Boot):** Type `Y` to sign kernel modules.

#### Custom Silent Script Installation:
```bash
chmod 755 FortiEDRSilentInstall_6.2.0_MNE.sh
sudo ./FortiEDRSilentInstall_6.2.0_MNE.sh
```

#### Linux Service Verification & Health Checks:
```bash
# Check service status
sudo systemctl status fortiedr-collector

# Verify loaded kernel modules
lsmod | grep -E "ensilo|fortiedr"
```

---

### 2.3 macOS Collector Deployment

Supported Versions: macOS Catalina (10.15), Big Sur (11.x), Monterey (12.x), Ventura (13.x), Sonoma (14.x).

#### Automated Installation via Jamf / MDM:
```bash
sudo installer -pkg ./FortiEDRInstallerOSX_6.2.0.pkg -target /
```

#### Generating Configuration Bootstrap (`CustomerBootstrap.jsn`):
```bash
./CustomBootstrapGenerator \
  --aggregator fortiedrconnectil.console.ensilo.com \
  --port 8081 \
  --password '<RegistrationPassword>' \
  --organization 'MNE' \
  --group 'Default Collector Group' > CustomerBootstrap.jsn
```

#### macOS System Extension / MDM Profile Whitelist:
When deploying via MDM (Jamf Pro), allowlist the following:
- **Team ID:** `A97R6J3L29`
- **Bundle IDs:**
  - `com.ensilo.ftnt`
  - `com.ensilo.ftnt.sysext`

---

## 🔒 3. Enterprise Network Port Matrix

All endpoints must be permitted to establish outbound TCP connections through perimeter firewalls (`fw-fortigate-hq-01`):

| Port | Protocol | Source | Destination | Function |
| :--- | :--- | :--- | :--- | :--- |
| `443` | HTTPS / TLS 1.3 | Admin / MNE Brain | `fortiedrconnectil.console.ensilo.com` | Management Console GUI & REST API |
| `8081` | Encrypted TCP | Endpoints (Workstations / Servers) | FortiEDR Cloud Aggregator | Collector Registration, Heartbeats, Policy Sync |
| `555` | Encrypted TCP | Endpoints (Workstations / Servers) | FortiEDR Cloud Core | Real-time Behavioral Evaluation & Blocking |

> [!IMPORTANT]
> **Proxy & Deep Packet Inspection Note:**
> Traffic on ports `8081` and `555` uses proprietary certificate-pinned TLS tunnels. Do **NOT** enable SSL Deep Packet Inspection (SSL-DPI) on FortiGate for these destination ports, as certificate re-signing will cause Collectors to reject the connection.
