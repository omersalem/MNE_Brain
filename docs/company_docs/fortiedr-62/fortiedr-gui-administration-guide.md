# FortiEDR 6.2 Cloud Management Console — Authoritative GUI Administration Guide

> **Organization:** `MNE`  
> **Console URL:** `https://fortiedrconnectil.console.ensilo.com`  
> **Release:** FortiEDR 6.2  
> **Source Attribution:** Fortinet FortiEDR 6.2 Administration Guide (Doc ID: 354083)  
> **Classification:** Engineering Operational Reference (Single Source of Truth)  

---

## 🧭 1. Global Navigation & Header Architecture

Every screen in the FortiEDR 6.2 Web Management Console is framed by the persistent top header:

```
[Fortinet Logo]  DASHBOARD | EVENT VIEWER | FORENSICS | COMMUNICATION CONTROL | SECURITY SETTINGS | INVENTORY | ADMINISTRATION    [Prevention/Simulation Toggle]  [User Profile: omersalem]
```

### Persistent Header Elements:
1. **Global Mode Toggle (Top Right):**
   - **Prevention (Green Switch):** All assigned security policies actively block malicious processes, terminate threats, and enforce network isolation rules according to configured playbooks.
   - **Simulation (Grey / Orange Warning):** Events are recorded and alerts are generated in Event Viewer and Forensics, but NO blocking, process termination, or file quarantine is executed. Used when onboarding new applications to baseline behavior.
2. **Organization / Multi-Tenancy Selector:**
   - In multi-tenant environments, the current active tenant is displayed and selected. For this environment, the organization is locked to **`MNE`**.
3. **User Profile Dropdown (`omersalem`):**
   - Displays logged-in username.
   - Menu items: **Change Password**, **Preferences**, **About**, and **Log Out** (`/login?logout`).
4. **Notification Badges:**
   - Red numeric pill next to **EVENT VIEWER** (e.g. `114` unhandled security events).
   - Numeric pill next to **COMMUNICATION CONTROL** (e.g. `2168` unresolved communicating applications).
   - Numeric pill next to **INVENTORY** (e.g. `11` pending actions or unassigned collectors).
   - Warning triangle next to **ADMINISTRATION** when component degradation, license thresholds, or certificate expirations require attention.

---

## 📊 2. Tab 1: DASHBOARD (`/#/dashboard`)

The Dashboard is the operational landing page presenting real-time telemetry across 6 primary widgets and report generation capabilities:

### Widget 1: SECURITY EVENTS (Top Left)
- **Visual Display:** Donut chart tracking unhandled and handled security events categorized by FortiEDR verdict:
  - **Malicious (Dark Red):** Confirmed malicious processes and ransomware behaviors.
  - **Suspicious (Red/Orange):** High-risk behaviors matching malicious heuristics.
  - **PUP (Yellow/Orange):** Potentially Unwanted Programs (adware, unauthorized miners).
  - **Inconclusive (Yellow):** Anomalous behaviors requiring manual review.
  - **Likely Safe (Grey):** Benign processes flagged by heuristics but verified safe.
- **View Toggles:**
  - **Computer Icon:** Aggregates by affected endpoints.
  - **Process Icon:** Aggregates by unique executable process name.
- **Interactions:** Clicking any chart segment or legend item immediately pivots to **EVENT VIEWER** filtered by that classification.

### Widget 2: COMMUNICATION CONTROL (Top Center)
- **Visual Display:** Donut chart tracking **Unresolved Communicating Applications**:
  - **Critical Vulnerability (Light Blue):** Applications with known high-severity CVEs communicating over the network.
  - **Low Reputation (Dark Blue):** Applications with poor FortiGuard reputation scores.
  - **Unknown And Unsigned Vendors (Light Grey):** Applications lacking digital signatures from trusted CAs.
- **Interactions:** Clicking any slice pivots to **COMMUNICATION CONTROL > Applications** filtered by vulnerability or reputation level.

### Widget 3: COLLECTORS (Top Right)
- **Visual Display:** Multi-bar status chart displaying health state of all registered endpoint agents:
  - **Running (Green):** Collector is active, connected to Aggregator/Core, and policies are synchronized.
  - **Degraded (Amber):** Collector service running but degraded (e.g., driver conflict, heavy load, or high memory).
  - **Disconnected (Red):** Collector offline or unable to reach Aggregator over port `8081/tcp`.
  - **Pending Reboot (Orange):** Collector installed with `NEEDREBOOT=1` or upgraded; awaiting system reboot to engage kernel hooks.
  - **Disabled (Grey):** Collector administratively disabled from the console.
  - **Unmanaged (Dark Grey):** Network devices discovered without an agent.
- **Dropdown Views:**
  - **General View:** Overall endpoint counts.
  - **Operating System View:** Breakdown by Windows, Linux, macOS.
  - **Collector Group View:** Breakdown by defined organizational groups.
  - **Core View:** Distribution across backend processing Cores.

### Widget 4: MOST TARGETED (Bottom Left)
- **Visual Display:** Horizontal bar rankings of the top 5 most attacked **Endpoints** or **Processes**, color-coded by event severity.
- **Toggles:** Switch between Device view and Process view.

### Widget 5: EXTERNAL DESTINATIONS (Bottom Center)
- **Visual Display:** Interactive global map showing outbound network connections established by monitored processes.
- **Controls:** Time selector dropdown (`Day`, `Week`, `Month`), Zoom in (`+`), Zoom out (`-`), Center map (`[ ]`).

### Widget 6: SYSTEM COMPONENTS (Bottom Right)
- **Visual Display:** Vertical health indicators for cloud infrastructure components:
  - **Cores:** Real-time prevention engines. Green = Healthy; Amber = Degraded; Red = Disconnected.
  - **Repositories:** Threat hunting elastic datastores.
  - **Aggregators:** Endpoint communication proxies.

### Report Generation:
- **Button:** `Generate Reports` (Top right above Collectors widget).
- **Function:** Opens the Executive Summary Report wizard to export high-level security posture PDFs over custom date ranges.

---

## 🚨 3. Tab 2: EVENT VIEWER

The Event Viewer is the primary investigation and incident remediation workspace.

### 3.1 Events Pane Layout & Columns
- **Event List Table:**
  - `Severity / Classification`: Malicious, Suspicious, PUP, Inconclusive, Likely Safe.
  - `Status`: Handled vs Unhandled.
  - `Process Name`: The executable that triggered detection.
  - `Device Name`: Endpoint hostname.
  - `User`: Windows/AD or local username running the process.
  - `Collector Group`: Group assignment of the device.
  - `Operating System`: Endpoint OS.
  - `Last Event Date/Time`: Exact timestamp (UTC+03:00 for MNE local operations).

### 3.2 Filtering Bar:
- **Status Filter:** All, Unhandled Only, Handled Only.
- **Classification Filter:** Multi-select checkboxes (Malicious, Suspicious, PUP, Inconclusive, Likely Safe).
- **Time Range:** Last Hour, Last 24 Hours, Last 7 Days, Last 30 Days, Custom Range.
- **Collector Group Dropdown:** Filter by specific department or subnet group.

### 3.3 Event Inspection Views:
Selecting an event in the table expands the detailed investigation drawer:
1. **Advanced Data:**
   - Executable path (e.g. `C:\Windows\System32\cmd.exe`).
   - Command line and arguments executed.
   - Hashes: MD5, SHA-1, SHA-256.
   - Digital signature verification: Signer, Certificate Authority, Validity status.
   - Parent process ID and parent executable path.
2. **Event Graph (Process Hierarchy Tree):**
   - Interactive visual graph displaying the full process tree.
   - Shows parent processes, spawned child processes, injected threads into external processes, opened network sockets, and file system modifications.
   - Suspicious and blocked nodes are highlighted in red.
3. **Geo Location:**
   - Displays destination IP, domain name, country, and ASN for network connection attempts.
4. **Automated Analysis:**
   - Cloud FortiGuard heuristic breakdown and sandbox detonation report.
5. **Stacks View:**
   - Low-level kernel and user-space memory stack trace identifying the exact DLL and memory address that violated memory integrity rules.

### 3.4 Incident Remediation & Actions:
At the top of the Event Details view, operators have immediate action controls:
- **Mark as Handled / Unhandled:** Clears or restores alert badge count.
- **Mark as Read / Unread:** Visual review tracking.
- **Isolate Device:**
  - Sever all network connectivity to the endpoint except secure encrypted tunnel to FortiEDR Aggregator (`8081/tcp`) and Core (`555/tcp`).
  - Device status changes to **Isolated** across the console.
  - **De-isolate Device:** Restores full network access after cleanup.
- **Remediate Device:**
  - Opens remediation wizard allowing the engineer to:
    1. `Kill Process`: Terminate active instances of the malicious executable.
    2. `Quarantine File`: Move file into encrypted FortiEDR quarantine vault.
    3. `Delete File`: Permanently remove executable and dropped payloads.
    4. `Clean Persistence`: Remove registry run keys, scheduled tasks, or services created by the malware.
    5. `Revert Changes`: Undo modified configuration settings.
- **Add Exception:**
  - If event is determined to be a false positive, click **Add Exception**.
  - Choose scope:
    - Target: Specific Collector Group or Entire Organization (`MNE`).
    - Matching criteria: Binary Hash (SHA-256), File Path, Signer/Certificate, or Destination IP/Port.
- **FortiEDR Connect (Live Shell):**
  - Establishes a real-time command-line shell directly onto the protected endpoint through the FortiEDR tunnel.
  - Enables running diagnostics, querying processes, reading event logs, and issuing management commands.
- **File Library / File Transfer:**
  - Upload forensic tools, cleanup scripts, or binaries to the endpoint.
  - Download suspicious files, malware samples, or memory dumps from the endpoint to the console.
- **Retrieve Memory Dump:**
  - Instructs Collector to dump process memory or full physical RAM into File Library for offline analysis.

---

## 🔍 4. Tab 3: FORENSICS (Threat Hunting)

Forensics provides deep, retroactive query capabilities across all endpoint telemetry stored in the Threat Hunting Repository.

### 4.1 Search Interface & Query Syntax:
- **Search Bar:** Supports Apache Lucene query syntax.
- **Common Query Fields:**
  - `Process.name`: Binary name (e.g. `Process.name:"powershell.exe"`).
  - `Process.commandLine`: Command line arguments (e.g. `Process.commandLine:*-enc*`).
  - `Connection.destinationIp`: Target IP address.
  - `Connection.destinationPort`: Target port.
  - `File.path`: Target file path.
  - `Registry.key`: Modified registry key.
  - `User.name`: Logged-in user account.
  - `Device.name`: Endpoint hostname.

### 4.2 The 6 Activity Tables:
Telemetry is organized into 6 tabs:
1. **Process Creation:** All process execution events, parent/child relationships, command-line arguments.
2. **Connection:** Inbound and outbound TCP/UDP connections, DNS queries, destination IPs and ports.
3. **File:** File create, modify, delete, and rename events.
4. **Registry:** Windows registry key creation, modification, and deletion.
5. **Loaded Modules:** DLLs, drivers, and libraries loaded into processes.
6. **User Logins:** Interactive, network, and service logon/logoff events.

### 4.3 Facets & Quick Filtering:
- Left sidebar displays dynamic facets: Top Processes, Top Users, Top Destination IPs, Top Devices.
- Clicking any facet applies an instant filter to the current query.

### 4.4 Investigation View & Export:
- **Investigation View:** Formats results as an interactive chronological timeline.
- **Export:** Click `Export` to save current search results to CSV.

---

## 🌐 5. Tab 4: COMMUNICATION CONTROL

Communication Control prevents unauthorized network communications, tracks software vulnerabilities, and enforces application firewalls on endpoints.

### 5.1 Applications Pane:
- **Table Columns:** Application Name, Vendor, Version, Reputation Score (0–100), Vulnerabilities (CVE count and severity), Communicating Endpoints count, Status (Resolved / Unresolved).
- **Actions:**
  - `Mark as Resolved / Unresolved`: Triage workflow indicator.
  - `Modify Policy Action`: Set rule for application (Allow, Block, Restrict, Log).
  - `Inspect Application Details`: View list of endpoints running the application, network destinations contacted, and associated CVE descriptions.

### 5.2 Policies Pane:
- Displays Communication Control policy rules:
  - **Predefined Policies:** Built-in rules for common enterprise applications.
  - **Policy Modes:** Simulation vs Protection.
  - **Rule Definition:**
    - Source: Collector Group.
    - Application: Identified binary or software group.
    - Direction: Inbound, Outbound, Both.
    - Destination: IP address, subnet, IP set, or Port.
    - Action: Allow, Block, Log.

---

## 🛡️ 6. Tab 5: SECURITY SETTINGS

Security Settings manages the core behavioral prevention rules, exclusions, exceptions, and automated response playbooks.

### 6.1 Security Policies Page:
- Out-of-the-box policies:
  1. **Pre-Execution Prevention:** Machine learning and FortiGuard AV scanning before binary execution.
  2. **Execution Prevention:** Kernel behavioral blocking against code injection, memory scraping, process hollowing, privilege escalation.
  3. **Ransomware Prevention:** Canary files, MBR protection, mass encryption detection and immediate volume shadow copy rollback.
  4. **Exfiltration Prevention:** Unauthorized outbound data tunneling and external file transfers.
  5. **Defacement Prevention:** Web server and critical service file modification protection.
- **Mode Control:** Each policy has an independent toggle for **Prevention** (Enforce) vs **Simulation** (Audit).

### 6.2 Exception Manager:
- Lists all active security event exceptions.
- View, edit, enable, disable, or delete exceptions created from Event Viewer.
- Exceptions can be scoped globally or restricted to individual Collector Groups.

### 6.3 Exclusion Manager:
- Configures path and process exclusions to optimize performance and prevent AV interoperability conflicts:
  - **Defining Exclusions:** Specify folder paths, exact file names, or process hashes to bypass deep behavioral monitoring.
  - **AV Product Interoperability:** Predefined exclusion templates for co-existing with third-party security software.
  - **Import / Export:** Export exclusion sets to JSON/CSV or import existing baseline files.

### 6.4 Application Control Manager:
- Manually block unauthorized software across the organization without waiting for threat detection:
  - Click `Add Application to be Blocked`.
  - Provide SHA-256 hash or executable path.
  - Set enforcement scope: All Collector Groups or designated groups.

### 6.5 Playbook Policies (Automated Incident Response):
- Automated response workflows executed the instant a threat is classified:
  - **Trigger:** When event severity reaches Malicious or Suspicious.
  - **Actions Configurable:**
    - `Isolate Device`: Automatically cut network connectivity.
    - `Kill Process`: Automatically terminate offending process.
    - `Quarantine / Delete File`: Remove payload.
    - `Notification`: Send urgent email to SOC distribution list.
  - **Assignment:** Assigned per Collector Group.

### 6.6 Threat Hunting Collection Profiles:
- Controls which telemetry categories endpoints record and upload to the Threat Hunting Repository.
- Create or clone profiles, toggle collection of: Process, Connection, File, Registry, Loaded Modules.
- Assign profiles to Collector Groups.

---

## 💻 7. Tab 6: INVENTORY

Inventory manages endpoint agents, collector groups, discovered unmanaged devices, and backend cloud components.

### 7.1 Collectors Tab:
- Table listing all installed FortiEDR agents:
  - `Device Name`: Computer hostname.
  - `Operating System`: Windows, Linux, macOS version.
  - `IP Addresses`: Network interface IPs.
  - `Collector Version`: Agent build number (e.g. `6.2.0.x`).
  - `Collector Group`: Current group membership.
  - `Status`: Running (Green), Degraded (Amber), Disconnected (Red), Pending Reboot, Disabled.
  - `Isolation Status`: Connected vs Isolated.
  - `Last Seen`: Timestamp of last heartbeat.
- **Collector Actions Menu (Select device -> Action):**
  - `Move to Collector Group`: Reassign device to another group.
  - `Isolate / De-isolate Device`: Toggle network quarantine.
  - `Enable / Disable Collector`: Temporarily turn agent protection on or off.
  - `Update Collector Version`: Trigger remote over-the-air agent upgrade.
  - `Export Logs`: Retrieve diagnostic logs bundle from the agent.
  - `Delete Collector`: Remove stale decommissioned device record from console.

### 7.2 Collector Groups:
- Logical grouping of devices (e.g., `Default Collector Group`, `Domain Controllers`, `Production Servers`, `Finance Workstations`).
- **Actions:**
  - `Define New Collector Group`: Specify group name and parent.
  - `Assign Policies`: Attach Security Policy, Communication Policy, and Playbook.
  - `Assign Collection Profile`: Attach Threat Hunting telemetry profile.

### 7.3 Unmanaged Devices & IoT Devices:
- Discovered network assets that do NOT have a FortiEDR Collector installed.
- Detected by collectors monitoring ARP and local subnet broadcasts.
- Displays MAC address, estimated OS, manufacturer OUI, IP address, and communicating ports.

### 7.4 System Components:
- Displays detailed status, IP addresses, resource utilization, and uptime for:
  - **Aggregators**
  - **Cores**
  - **Repositories**
- Includes action to `Export Logs` for Cores and Aggregators for Fortinet technical support.

---

## ⚙️ 8. Tab 7: ADMINISTRATION

The Administration tab provides administrative controls, identity management, licensing, and enterprise integrations.

### 8.1 Licensing:
- Displays license tier, total seats purchased, active seats used, and support contract expiration dates.

### 8.2 Requesting & Obtaining Collector Installers:
- **Download Custom Installer:** Generates pre-configured MSI / PKG / RPM / DEB installer packages with tenant URL, organization name (`MNE`), and registration password already embedded.
- **Download Generic Installer:** Raw installer packages requiring CLI parameters (`AGG=`, `PWD=`, `ORG=`).

### 8.3 Loading Server Certificate:
- Upload custom SSL/TLS certificates and private keys for the management console domain name.

### 8.4 User Management & RBAC:
- **User Accounts:** Create and manage operators.
- **Roles:** Super Administrator, Administrator, SOC Analyst, Read-Only Auditor.
- **Scope:** Assign user access to specific organizations (`MNE`) or global hoster view.

### 8.5 Authentication & SSO:
- **Local DB:** Username and password authentication.
- **LDAP Authentication:** Connect to Active Directory domain controllers (`MNE-DC1.mne.gov`).
- **SAML 2.0 Identity Provider:** Configure single sign-on with Azure AD, Okta, or FortiAuthenticator.
- **Two-Factor Authentication (2FA):** Enforce TOTP or email tokens.
- **Password Policy:** Configure minimum length, complexity, history, and lockout thresholds.

### 8.6 Integrations & Connectors:
- **FortiGate Integration:** Push malicious IP addresses and compromised device MACs to FortiGate firewalls to enforce automated network-edge quarantine.
- **FortiAnalyzer / Syslog:** Forward security events and incident telemetry in RFC-5424 syslog or JSON format.
- **FortiSandbox:** Submit suspicious zero-day executables for dynamic cloud detonation.
- **FortiNAC:** Trigger automated VLAN isolation and switch port quarantine.
- **Public Cloud Connectors:** AWS GuardDuty, Google Cloud SCC integration.
- **Action Manager:** Configure custom webhooks and REST API event dispatchers.

### 8.7 SMTP & Notifications:
- Configure mail relay server IP, authentication, sender email, and alert distribution lists for automated incident ticketing.
