# Ministry Network Operations Manual

# Ministry Network Operations Manual

**Version:** 3.0 (Final Verified)

**Date:** December 2025

\---

## 1\. Overview of the Ministry Network

The Ministry network is designed like a highly secured office building with clear roles for each device and layer.

* **Fujitsu Core Switch (The Hub):** The main aggregation and switching layer. All zones ultimately connect here.
* **FortiGate Firewall (The Receptionist):** Internet edge and user gateway. Controls who enters and exits the network and who can access the server zone.
* **Cisco FTD Firewall (The Vault Guard):** Server‑side firewall that strictly protects data center segments.
* **Cisco Core Switch (The Elevator):** Campus core that connects all floors and access switches to the data center.
* **SAN (The Archives):** Physically separated storage network over fiber, dedicated to high‑speed data movement between servers and storage.

\---

## 2\. Master Device Inventory

### 2.1 Core Network Devices

|**Device Name**|**Hardware Model**|**Management IP**|**Role / Job Description**|
|-|-|-|-|
|**MNE-CoreSw2**|**Fujitsu Switch**|`172.23.70.71`|**Core Fabric Switch.** Physical center of the network, interconnecting firewalls, campus, and servers. Handles high‑throughput L2/L3 forwarding between zones. 1|
|**FG-MNE-B**|**FortiGate 601E**|`10.11.12.1`|**User Edge \& Internet Gateway.** Default gateway for staff VLANs, manages WAN links to Internet and branches, and enforces security policies for user traffic. 2222|
|**Cisco FTD**|**Cisco Firepower 3105**|`172.23.70.78`|**Server‑Side Firewall.** Creates the server security zone, performs deep inspection, and enforces access from users and external sources to servers. 3|
|**F5 WAF**|**F5 BIG-IP r2000**|`172.23.70.89`|**Web Application Firewall.** Protects the public ESADAD website, stopping SQL injection, XSS, and bot attacks before they reach the web servers. Connecteddirectly to Cisco CoreSwitch1 via Copper Ports Twe 1/0/12 \& 2/0/12|
|**CoreSwitch1**|**Cisco 9500 Stack**|`172.23.70.254`|**Campus Aggregation Switch.** Aggregates all floor access switches (Basement–Floor 6) and uplinks to the Fujitsu Core via 40G link. 4444|

\---

## 3\. Storage Area Network (SAN)

*The SAN is physically separated from the user network and uses dedicated Orange Fiber cabling (Fibre Channel).*

### 3.1 SAN Device Roles

|**Device**|**Model**|**Job Description**|
|-|-|-|
|**SAN Switch**|**Brocade / Fujitsu**|**Storage Fabric Switch.** Connects servers to disks using Fibre Channel, ensuring the Backup Server can see tapes while regular servers only see authorized LUNs.|
|**Primary Storage**|**ETERNUS AF250 S3**|**All‑Flash Primary Storage.** Hosts active databases and virtual machines; optimized for high performance and low latency.|
|**Tape Library**|**ETERNUS LT140**|**Long‑Term Archive.** Writes data to LTO magnetic tapes for disaster recovery. Used when disks are corrupted or compromised.|
|**Backup Server**|**Windows Server**|**Central Backup Orchestrator.** Runs backup software and is the *only* host allowed to communicate with both the Flash Storage and Tape Library.|
|**ESXi Hosts**|**Fujitsu Servers**|**Virtualization Hosts.** Run Windows/Linux VMs. Do not store data locally; all I/O is to AF250 over the SAN.|

### 3.2 SAN Connection Matrix (Fiber Cabling)

|**SAN Switch Port**|**Connected Device**|**Details**|
|-|-|-|
|**Port 0, 1, 2, 3**|**ESXi Hosts 1–4**|Fiber connectivity for VMs to boot and read/write operating system and data volumes.|
|**Port 8**|**Backup Server**|Dedicated path for backup and restore operations.|
|**Port 9**|**Tape Library**|Link used to write backup data to LTO tape cartridges.|
|**Port 42, 43**|**Flash Storage**|Dual connections to Storage Controllers A \& B for redundancy and load balancing.|

\---

## 4\. Server \& VM Inventory (The Vault)

These are the critical services running on the **ESXi Cluster** (connected to Fujitsu ports 0/1–0/18).

Servers are grouped by function and VLAN.

### 4.1 Core Application Servers (VLAN 71 – 172.23.71.x)

### 4.1.1 Database \& Email Services

* **MNEPDB-SRV** (`172.23.71.73`) – Primary SQL Database.
* **EXCHANGESRV1** (`172.23.71.35`) – Primary Email Server.
* **EXCHANGESRV2** (`172.23.71.36`) – Secondary Email Server.
* **report\_oracle\_srv\_new\_1** (`172.23.71.60`) – Oracle Reporting Server.
* **OEM-SRV** (`172.23.71.68`) – Oracle Enterprise Manager.

### 4.1.2 Collaboration \& Document Management

* **sharepiont-srv** (`172.23.71.149`) – SharePoint Document Portal.
* **OpenKMweb-srv** (`172.23.71.142`) – Document Management System.
* **Archive-srv** (`172.23.71.56`) – Primary Archiving Server.
* **Departmentarchive-srv** (`172.23.71.21`) – Department Archiving Server.
* **FileSharing-srv** (`172.23.71.100`) – File Sharing Server.
* **FILEPRINTSERVER\_New** (`172.23.71.23`) – File and Print Server.

### 4.1.3 Web Services

* **Web\_Page\_Mne** (`172.23.71.66`) – Ministry Website Server.
* **website-srv** (`172.23.71.59`) – Ministry Website Server.
* **Web\_Portal\_Srv** (`172.23.71.103`) – Web Portal Server.

### 4.1.4 Infrastructure Services

* **MNE-DC1** (`172.23.71.27`) – Primary Domain Controller.
* **MNE-DC2** (`172.23.71.28`) – Secondary Domain Controller.
* **MNE-DHCP** (`172.23.71.32`) – DHCP Server.
* **WSUS-SRV** (`172.23.71.80`) – Windows Update Server.
* **SystemCenter** (`172.23.71.84`) – System Center Management.

### 4.1.5 Security Services

* **TrendMicro-DDI** (`172.23.71.81`) – Security / Threat Detection.
* **Antivirus-srv** (`172.23.71.199`) – Antivirus Management.
* **Sophos Mail Protection** (`172.23.71.39`) – Email Security.
* **MNE-FIleScan-Srv** (`172.23.71.171`) – File Scanning Server.
* **EDRCore** (`172.23.71.130`) – Endpoint Detection and Response.
* **FAZ-2024** (`172.23.71.206`) – FortiAnalyzer.
* **FortiManager-VM** (`172.23.71.205`) – FortiManager.

### 4.1.6 Specialized Applications

* **Tools-srv** (`172.23.71.111`) – IT Tools Server.
* **Indust-Dev** (`172.23.71.47`) – Industrial Development Server.
* **Indust\_Prod** (`172.23.71.48`) – Industrial Production Server.
* **mnep\_dr\_srv** (`172.23.71.75`) – Disaster Recovery Server.
* **support-srv** (`172.23.71.9`) – Support Services.
* **mdt01** (`172.23.71.72`) – Deployment Toolkit.
* **Esooq-srv** (`172.23.71.146`) – e-Sooq Application.
* **Company\_Service** (`172.23.71.83`) – Company Services.
* **Sql\_Web\_srv** (`172.23.71.87`) – SQL Web Interface.
* **Witness-SRV** (`172.23.71.55`) – Cluster Witness Server.
* **UXP\_adapter\_srv2** (`172.23.71.78`) – UXP Adapter.
* **MYQ\_SRV** (`172.23.71.71`) – Print Management.

### 4.2 Database Servers (VLAN 75 – 172.23.75.x)

* **Manus-Srv** (`172.23.75.200`) – Dedicated Database Server.

### 4.3 Web \& Public Facing Servers (VLAN 79 – 172.23.79.x)

* **ESADAD-SRV** (`172.23.79.77`) – ESADAD Public Portal.
* **procedures-srv** (`172.23.79.79`) – Procedures System.
* **ESADADTEST-SRV** (`172.23.79.80`) – ESADAD Test Server.
* **ESADADMTIT-PRODUCTION** (`172.23.79.81`) – ESADAD Production.
* **ESADAD-MIND-SRV** (`172.23.79.83`) – ESADAD MIND Server.
* **ESADADMTIT-TEST** (`172.23.79.78`) – ESADAD MTIT Test.
* **FMC Ultimate Configurator** (`172.23.79.100`) – FMC Configurator.

### 4.4 Development \& Testing (VLAN 30 – 172.23.30.x)

* **DEV\_ABRS** (`172.23.30.102`) – Development Server.
* **Staging\_ABRS** (`172.23.30.100`) – Staging Server.
* **UAT\_ABRS** (`172.23.30.101`) – User Acceptance Testing Server.
* **Automation\_ABRS** (`172.23.30.105`) – Automation Server.

### 4.5 Management \& Infrastructure (VLAN 69 – 172.23.69.x)

* **VMware vCenter Server 7.3j** (`172.23.69.38`) – vCenter Server.
* **Veeam Proxy** (`172.23.69.71`) – Backup Proxy.
* **vCenter FTP Backup Server** (`172.23.69.110`) – Backup Storage.

### 4.6 Other VLANs \& Services

**VLAN 74 (ERCompany):**

* **Company\_reg\_App** (`172.23.74.10`) – Company Registration Application.
* **Company\_reg\_DB** (`172.23.74.12`) – Company Registration Database.

**VLAN 72 (Trade):**

* **trade-srv2** (`172.23.72.2`) – Trade Server.
* **wipo-publish** (`172.23.72.54`) – WIPO Publishing.
* **Hasasneh\_New\_Server** (`172.23.72.100`) – Hasasneh Server.
* [**sp2010-srv.mne.gov**](http://sp2010-srv.mne.gov) (`172.23.72.114`) – SharePoint 2010.
* **sp2017-srv** (`172.23.72.210`) – SharePoint 2017.
* **sp2018-srv** (`172.23.72.212`) – SharePoint 2018.

**VLAN 78 (Application):**

* **Apex-srv** (`172.23.78.50`) – Apex Application Server.
* **Ticket-srv** (`172.23.78.150`) – Ticketing Server.

**VLAN 55 (Mind\_UXP):**

* **mind\_uxp\_adapter** (`172.23.55.55`) – MIND UXP Adapter.
* **mind\_uxp\_portal** (`172.23.55.60`) – MIND UXP Portal.
* **mind\_uxp\_Security** (`172.23.55.70`) – MIND UXP Security.
* **mind\_uxp\_Connector** (`172.23.55.80`) – MIND UXP Connector.

**VLAN 81 (HR Clock):**

* **HR\_SRV** (`172.23.81.72`) – HR Server.

**VLAN 88 (UXP):**

* **UXP Security Server** (`172.23.88.20`) – UXP Security.
* **uxp\_portal server** (`172.23.88.30`) – UXP Portal.
* **uxp connector server** (`172.23.88.40`) – UXP Connector.
* **egovadapter-srv1** (`172.23.88.215`) – eGov Adapter.

**VLAN 70 (Mgmt):**

* **Cisco\_Secure\_FW\_Mgmt\_Cente** (`172.23.70.77`) – Cisco FMC.

\---

## 5\. Master Connection Matrix (Cables \& Ports)

Use this section to find where physical cables are terminated.

### 5.1 Data Center Core (Fujitsu) Connections

All connections in this table use **10G/40G Fiber Optic Cables (Orange)**.

|**Source Device**|**Source Interface**|**Destination Device**|**Destination Interface**|**Traffic Type / Description**|
|-|-|-|-|-|
|**Fujitsu Core**|`0/47`|**FortiGate**|`x1`|**User LAN (VLAN 19–26).** Staff Internet and user traffic. 5555|
|**Fujitsu Core**|`0/40`|**FortiGate**|`x2`|**Transit (VLAN 200).** Routed traffic toward server networks. 6666|
|**Fujitsu Core**|`0/39`|**Cisco FTD**|`Po1`|**Outside Interface.** Traffic entering the server zone. 7777|
|**Fujitsu Core**|`0/46`|**Cisco FTD**|`Po2`|**Inside Interface.** Traffic exiting to server VLANs. 8888|
|**Fujitsu Core**|`0/44`|**Cisco Core**|`Po44`|**Campus Uplink.** 40Gbps uplink to floors. 9999|
|**Fujitsu Core**|`0/1–18`|**ESXi Servers**|*NIC*|**Server Data.** Application and service traffic for ESXi VMs. 10101010|

### 5.2 Campus Floors (Cisco Core Downlinks)

**Management IP:** 172.23.70.70 \& 71

|**Cisco Core Port**|**Neighbor Device**|**IP Address**|**Role / Location**|
|-|-|-|-|
|**Twe 1/0/12**|**F5 WAF**|172.23.70.89|**WAF Link 1** (VLAN 9 \& 10).|
|**Twe 2/0/12**|**F5 WAF**|172.23.70.89|**WAF Link 2** (Redundant).|
|**Twe 2/0/6**|**DMZ Switch**|`172.23.9.254`|**Legacy DMZ** Connection. 11|
|**Twe 1/0/7**|**Switch F\_-1**|`172.23.70.220`|**Basement Staff.** 12|
|**Twe 1/0/8**|**Switch Khadamat**|`172.23.70.219`|**Basement Services.** 13|
|**Twe 1/0/9**|**Switch F0**|`172.23.70.221`|**Ground Floor.** 14|
|**Twe 1/0/1**|**Switch F1**|`172.23.70.222`|**Floor 1.** 15|
|**Twe 1/0/3**|**Switch F2**|`172.23.70.223`|**Floor 2.** 16|
|**Twe 1/0/2**|**Switch F3**|`172.23.70.224`|**Floor 3.** 17|
|**Twe 1/0/4**|**Switch F4**|`172.23.70.225`|**Floor 4.** 18|
|**Twe 1/0/5**|**Switch F5**|`172.23.70.226`|**Floor 5.** 19|
|**Twe 1/0/6**|**Switch F6**|`172.23.70.227`|**Floor 6.** 20|
|**Twe 2/0/11**|**VoIP Router**|`172.23.76.2`|**Voice Gateway.** 21|
|**Twe 2/0/10**|**CUCM Server**|`172.23.76.11`|**Call Manager.** 22|

### 5.3 FortiGate 601E Physical Topology

**Device Role:** Edge Security \& User Gateway

**Hostname:** FG-MNE-B (Primary)

**Management IP:** 172.23.70.4

|**Interface**|**Physical Port**|**Connected To**|**Remote Port**|**Cable / Link Type**|**Function / Traffic**|
|-|-|-|-|-|-|
|**WAN (Primary)**|`Port 2`|**ISP Router**|*(ISP Handoff)*|Copper/Fiber (1G)|**Main Internet Access.** Default route towards ISP.|
|**WAN (Legacy)**|`Port 1`|**Legacy ISP Router**|*(ISP Handoff)*|Copper (1G)|Backup / Government private link.|
|**WAN (Branch)**|`Port 3`|**Branch Router**|*(Router Port)*|Copper (1G)|Connectivity to remote offices.|
|**LAN Trunk**|`x1` (Agg)|**Fujitsu Core Switch**|`Port 0/47`|**10G SFP+ Fiber**|**User Data.** Carries all floor VLANs (19–26, 42, 76).|
|**Transit Link**|`x2` (Agg)|**Fujitsu Core Switch**|`Port 0/40`|**10G SFP+ Fiber**|**Server Data.** Routes traffic to the data center (VLAN 200).|
|**HA Heartbeat**|`ha`|**Secondary FortiGate**|`ha`|Copper (Direct)|**Cluster Sync.** Keeps the standby unit updated.|
|**Management**|`mgmt`|**Mgmt Switch / Network**|*(Switch Port)*|Copper (1G)|**Admin Access.** Out‑of‑band management.|

### 5.4 F5 WAF Physical Topology

**Device Role:** Application Security and Load Balancing

**Hostname:** `F5-WAF-01`

**IP Address:** `172.23.70.89`

**VLANs Used:**

* **VLAN 9** – Internal (server‑side)
* **VLAN 10** – External (client / Internet‑facing)

The F5 WAF connects to the Cisco Core via a 2‑Port LACP trunk for high availability and bandwidth.

|**Interface**|**Physical Port (F5)**|**Connected To**|**Remote Port**|**Cable / Link Type**|**Function / Traffic**|
|-|-|-|-|-|-|
|**Trunk Member 1**|`1.1`|**Cisco Core Switch**|`Twe 1/0/12`|Copper (RJ45)|Data trunk for **VLAN 9 (Internal)** and **VLAN 10 (External)**.|
|**Trunk Member 2**|`1.2`|**Cisco Core Switch**|`Twe 2/0/12`|Copper (RJ45)|Redundant trunk member carrying VLAN 9 and VLAN 10.|
|**Management**|`mgmt`|**Mgmt Switch / Management Network**|`(Switch Port)`|Copper (1G)|**Admin Access.** Out‑of‑band configuration and monitoring.|

### 

### 5.5 Cisco FTD 3105 Physical Topology

**Device Role:** Server Gateway \& Internal Security

**Hostname:** `Cisco FTD`

**Management IP:** `172.23.70.78`

|**Interface**|**Interface Name**|**Connected To**|**Remote Port**|**Cable / Link Type**|**Function / Traffic**|
|-|-|-|-|-|-|
|**Port-channel1**|`Outside`|**Fujitsu Core Switch**|`Port 0/39`|**10G Fiber**|**Ingress.** Traffic entering the server zone (VLAN 200). 2222|
|**Port-channel2**|`Inside`|**Fujitsu Core Switch**|`Port 0/46`|**10G Fiber**|**Egress.** Traffic exiting to server VLANs (71, 75, 79, etc.). 3333|
|**Mgmt 1/1**|`management`|**Fujitsu Core Switch**|`Port 0/34`|**1G Copper**|**Admin Access.** Out‑of‑band management (VLAN 70). 4444|

\---

## 6.Cable Types In Data Center

### A. Data Center Core (The Fiber Backbone)

|**Source Device**|**Interface**|**Destination**|**Interface**|**Physical Cable Type**|**Traffic**|
|-|-|-|-|-|-|
|**Fujitsu Core**|`0/47`|**FortiGate**|`x1`|**10G Fiber (SFP+)**|User LAN|
|**Fujitsu Core**|`0/40`|**FortiGate**|`x2`|**10G Fiber (SFP+)**|Transit|
|**Fujitsu Core**|`0/39`|**Cisco FTD**|`Po1`|**10G Fiber (SFP+)**|FTD Outside|
|**Fujitsu Core**|`0/46`|**Cisco FTD**|`Po2`|**10G Fiber (SFP+)**|FTD Inside|
|**Fujitsu Core**|`0/44`|**Cisco Core**|`Po44`|**40G Fiber (QSFP)**|Campus Uplink|
|**Fujitsu Core**|`0/1-18`|**ESXi Cluster**|*NICs*|**10G Fiber (SFP+)**|Network Data|
|SAN Switch|**Port 0, 1, 2, 3**|**ESXi Hosts 1–4**||16G/32G Fiber (FC)||
|SAN Switch|**Port 8**|**Backup Server**||16G Fiber (FC)||
|SAN Switch|**Port 9**|**Tape Library**||8G Fiber (FC)||
|SAN Switch|**Port 42, 43**|**Flash Storage**||32G Fiber (FC)||

## **B. The "Copper" Exception (F5 \& Mgmt)**

|**Source Device**|**Interface**|**Destination**|**Interface**|**Physical Cable Type**|**Traffic**|
|-|-|-|-|-|-|
|**Cisco Core**|`Twe 1/0/12`|**F5 WAF**|*Port 1*|**1G Copper (RJ45)**|WAF Trunk|
|**Cisco Core**|`Twe 2/0/12`|**F5 WAF**|*Port 2*|**1G Copper (RJ45)**|WAF Trunk|
|**Cisco Core**|`mgmt`|F5 WAF|`(Switch Port)`|Copper (1G)|**Admin Access.** Out‑of‑band configuration and monitoring.|
|**Fujitsu Core**|`0/34`|**Cisco FTD**|`Mgmt`|**1G Copper (RJ45)**|Management|
|**Fujitsu Core**|`0/33`|**SAN Switch**|`Eth0`|**1G Copper (RJ45)**|Management|
|FortiGate|Port 2|ISP Router|WAN|Copper (RJ45)  1 Gbps / 100M|Main Internet|
|FortiGate|Port 1|ISP Router|Goverment VPN|Copper (RJ45)  1 Gbps / 100M|other ministries VPN connection|
|FortiGate|Port 3|Branches|WAN|Copper (RJ45)  1 Gbps / 100M|Branches via MPLS|
|||||||

# Branch Network Operations

**Scope:** Remote Ministry Offices (13 Sites)
**Architecture:** Standardized "Split-Tunnel" Design with Local Voice Survivability.

\---

## **1. Branch Architecture Overview**

Every Ministry branch follows a strict **3-Device Template**. If you know how one branch works, you know how they all work.

### **The Three Core Devices**

1. **Branch FortiGate (The Gateway):**

   * **Role:** It is the Router and Firewall. It connects the branch to the **Ministry HQ** (Private WAN) and the **Internet** (Public).
   * **Job:** It decides if traffic stays local, goes to HQ (via VPN/MPLS), or goes to Google/Internet.
2. **Cisco Access Switch (The Connector):**

   * **Role:** Connects all staff PCs, IP Phones, Printers, and Cameras.
   * **Job:** Provides Power over Ethernet (PoE) to phones. It links everything to the FortiGate.
3. **Cisco Router (The Voice Backup):**

   * **Role:** Voice Gateway (SRST - Survivable Remote Site Telephony).
   * **Job:** It usually does nothing while the network is healthy. If the connection to HQ breaks, **Phones register here** so staff can still make local calls via the PSTN (Telephone Lines).

## **2. Standard IP Addressing Schema**

Each branch is assigned a unique **Subnet ID** (e.g., `10.201.18.x` for Jenin). The last octet always follows this rule:

|**Device / Role**|**IP Address Rule**|**Example (Jenin)**|
|-|-|-|
|**Network Subnet**|`10.xxx.18.0/24`|`10.201.18.0`|
|**Default Gateway**|`.1` (FortiGate)|`10.201.18.1`|
|**Voice Gateway**|`.2` (Cisco Router)|`10.201.18.2`|
|**Switch Management**|`.3` (Cisco Switch)|`10.201.18.3`|
|**Printers/Cameras**|`.10 - .49`|`10.201.18.20`|
|**DHCP Range (Users)**|`.50 - .254`|`10.201.18.55`|

|**Branch Name**|**Subnet**|**Gateway (FW)**|**Router (Voice)**|**Switch (Mgmt)**|
|-|-|-|-|-|
|**Jenin**|`10.201.18.0/24`|`.1`|`.2`|`.3`|
|**Nablus**|`10.131.18.0/24`|`.1`|`.2`|`.3`|
|**Tulkarm**|`10.165.18.0/24`|`.1`|`.2`|`.3`|
|**Qalqilya**|`10.180.18.0/24`|`.1`|`.2`|`.3`|
|**Salfeet**|`10.235.18.0/24`|`.1`|`.2`|`.3`|
|**Tubas**|`10.230.18.0/24`|`.1`|`.2`|`.3`|
|**Hebron**|`10.40.18.0/24`|`.1`|`.2`|`.3`|
|**Bethlehem**|`10.60.18.0/24`|`.1`|`.2`|`.3`|
|**Jericho**|`10.211.18.0/24`|`.1`|`.2`|`.3`|
|**Jerusalem**|`10.70.18.0/24`|`.1`|`.2`|`.3`|
|**Ramallah Gold**|`10.110.19.0/24`|`.1`|`.2`|`.3`|
|**Hebron Gold**|`10.40.19.0/24`|`.1`|`.2`|`.3`|
|**Nablus Gold**|`10.131.19.0/24`|`.1`|`.2`|`.3`|

## **4. Connection Matrix (Cabling Guide)**

Use this table to trace cables inside the Branch Rack.

|**Device A**|**Interface**|**Device B**|**Interface**|**Description**|
|-|-|-|-|-|
|**FortiGate**|`wan1`|**ISP Router**|*WAN Port*|**Private Link to HQ**1.|
|**FortiGate**|`wan2`|**ISP Router**|*WAN Port*|**Public Internet**2.|
|**FortiGate**|`internal`|**Cisco Switch**|*Uplink*|**Main LAN Trunk**3.|
|**Cisco Switch**|`Gi48` (or 46)|**Cisco Router**|`Gi0/0`|**Voice Gateway Link**4444.|
|**Cisco Switch**|`Gi1 - Gi40`|**Users**|*NIC*|**PCs \& Phones**.|
|**Cisco Router**|`POTS/FXO`|**Wall Jack**|*RJ11*|**Local Phone Lines** (PSTN).|

## 7\. Data Flow Scenarios (How Traffic Moves)

**7.1 Scenario 1 – Inbound Public Access to Web Portal (The Hairpin)**

Context: A citizen accesses the Ministry website (ESADAD) from home.
Path Logic: Internet → Edge FW → Server FW → Cisco Core (WAF) → Server.

1. **Internet** sends traffic to **FortiGate** on **Port 2** (WAN IP: `213.6.17.30`).
2. **FortiGate** applies VIP and routes traffic out **Port x2** (Transit Link) to the **Fujitsu Core**.
3. **Fujitsu Core** receives traffic on **Port 0/40** and switches it to **Port 0/39**.
4. **Cisco FTD** receives traffic on **Port-channel1** (Outside: `172.23.200.2`), inspects it, and routes it out **Port-channel2** (Inside).
5. **Fujitsu Core** receives traffic on **Port 0/46**. It sees the destination is the WAF (VLAN 10) which lives on the Cisco Core.
6. **Fujitsu Core** sends traffic DOWN the 40G uplink **Port 0/44** to the **Cisco Core** (`Po44`).
7. Cisco Core sends traffic via Copper Link to F5 WAF **(Twe 1/0/12 \& 2/0/12)** .
8. **F5 WAF** inspects (SQLi/XSS, bots) and returns clean traffic to **Cisco Core** via the same Trunk on **VLAN 9**.
9. **Cisco Core** sends the clean traffic back UP via **Po44** to the **Fujitsu Core**.
10. **Fujitsu Core** delivers traffic via **Ports 0/1–18** to the **ESXi Web Server** (VLAN 79).

### 7.2 Scenario 2 – Staff Browsing the Internet

**Context:** An employee on Floor 2 visits Google.

**Path Logic:** Campus → Core → Edge → ISP.

1. User PC (VLAN 21) sends traffic to Floor 2 switch (`F2`).
2. Floor 2 switch forwards to Cisco Core (Port `Twe 1/0/3`).
3. Cisco Core aggregates and sends through `Po44` to Fujitsu Core (Port `0/44`).
4. Fujitsu Core forwards to default gateway FortiGate (Port `0/47`).
5. FortiGate receives on Port `x1` (LAN), applies NAT, and sends out Port `2` to the Internet.

### 7.3 Scenario 3 – Internal User Accessing File Server

**Context:** Staff on Floor 1 opens a file on the main file server.

**Path Logic:** Campus → Edge FW → Server FW → Server.

1. User PC sends traffic to Floor 1 switch → Cisco Core (`Twe 1/0/1`) → Fujitsu Core (`0/44`).
2. Fujitsu Core forwards to user gateway FortiGate (via `0/47 → x1`).
3. FortiGate routes to server subnet (`172.23.71.x`) via Transit Link: out Port `x2` to Fujitsu Core (`0/40`).
4. Fujitsu Core forwards to Cisco FTD via `0/39` (**Outside**).
5. Cisco FTD inspects traffic and permits it out Port‑channel2 (**Inside**) to Fujitsu Core (`0/46`).
6. Fujitsu Core delivers to ESXi Host via Ports `0/1–18`.
7. **Storage Step:** ESXi host retrieves file data from Flash Storage via SAN Switch (Orange Fiber, Port `0 → 42`).

### 7.4 Scenario 4 – Branch Office Accessing HQ Database

**Context:** User in Jenin accesses database at HQ.

**Path Logic:** Branch → Private WAN → HQ Edge → HQ Server FW → Server.

1. Jenin PC sends traffic to Jenin Switch → Jenin FortiGate (internal).
2. Jenin FortiGate routes via `wan1` (`172.27.13.26`) over private MPLS.
3. HQ FortiGate receives on Port `3` (Branch WAN).
4. HQ FortiGate routes traffic via Port `x2` to Fujitsu Core (`0/40`) → Cisco FTD (`0/39`).
5. Cisco FTD permits and sends via `Po2` → Fujitsu Core (`0/46`) → Database Server.

### 7.5 Scenario 5 – Server Downloading Updates

**Context:** Exchange Server downloads a patch from Microsoft.

**Path Logic:** Server → Server FW → Edge FW → Internet.

1. Server sends traffic to Fujitsu Core → Cisco FTD (Inside, `Po2`).
2. Cisco FTD routes out Port‑channel1 (**Outside**) to Fujitsu Core (`0/39`).
3. Fujitsu Core sends to FortiGate via `0/40 → x2`.
4. FortiGate applies NAT and sends out Port `2` to the Internet.

### 7.6 Scenario 6 – External VoIP Call (PSTN)

**Context:** User dials an external mobile number.

**Path Logic:** Phone → Cisco Core → CUCM → VoIP Router → PSTN.

1. IP Phone sends signaling to Floor Switch → Cisco Core.
2. Cisco Core forwards to CUCM Server via Port `Twe 2/0/10` (VLAN 76).
3. CUCM sets up the call.
4. Cisco Core routes RTP audio to VoIP Router via Port `Twe 2/0/11`.
5. VoIP Router sends call out E1/T1/SIP trunk to PSTN.

### 7.7 Scenario 7 – Internal VoIP Call (Local)

**Context:** User A calls User B in the same building.

**Path Logic:** Phone A → Network → Phone B (Layer 2 only).

1. Phone A signals via CUCM (through Cisco Core) to set up the call.
2. Audio flows directly: Phone A → Floor Switch → Cisco Core → Floor Switch → Phone B.
3. Traffic stays on VLAN 76 and does **not** traverse firewalls or Fujitsu Core.

### 7.8 Scenario 8 – User Printing (Cross‑VLAN)

**Context:** User (VLAN 21) prints to printer (VLAN 42).

**Path Logic:** User → Gateway (Routing) → Printer.

1. User PC sends print job to Cisco Core → Fujitsu Core (`0/44`).
2. Fujitsu Core sends to default gateway FortiGate (`0/47`).
3. FortiGate routes from VLAN 21 to VLAN 42 and sends back out Port `x1`.
4. Fujitsu Core forwards down to Cisco Core (`0/44 → Po44`).
5. Cisco Core sends to Floor Switch hosting the printer → Printer.

### 

7.9 Scenario 9 – Internal Management Access
Context: Admin on VLAN 50 logs into Cisco FTD and F5 WAF.

Path Logic: Admin → Gateway → Mgmt Network → Device.

Path A: Managing the FTD (Connected to Fujitsu)

1. Admin PC sends traffic to Cisco Core → Fujitsu Core → FortiGate (x1).
2. FortiGate routes from Admin VLAN 50 to Mgmt VLAN 70.
3. FortiGate returns traffic to Fujitsu Core.
4. Fujitsu Core delivers traffic to Cisco FTD Mgmt port via 0/34.

Path B: Managing the F5 WAF via Cisco Core

1. Admin PC sends traffic to Cisco Core → Fujitsu Core → FortiGate.
2. FortiGate routes to Mgmt VLAN 70 and sends back to Fujitsu Core.
3. Fujitsu Core sends traffic DOWN to Cisco Core via Po44.
4. Cisco Core delivers traffic to F5 WAF Mgmt Port (via Twe 1/0/13 or similar copper port).

### 7.10 Scenario 10 – Nightly Backup (SAN Traffic)

**Context:** Backup Server saves the database to tape.

**Path Logic:** Storage → SAN Switch → Backup Server → SAN Switch → Tape.

1. Backup Server sends **Read** via fiber to SAN Switch Port `8`.
2. SAN Switch forwards to Flash Storage via Port `42`.
3. Flash Storage returns data to Backup Server (`Storage → 42 → 8 → Server`).
4. Backup Server writes data to Tape Library (`Server → 8 → 9 → Tape`).

\---

## 8\. Branch Offices – Data Flow Scenarios

### 8.1 Scenario 11 – Branch‑to‑Branch Data Transfer

**Context:** Staff in Jenin sends a file directly to staff in Tulkarm.

**Path Logic:** Branch A → HQ Hub → Branch B (hairpin through HQ).

1. Jenin PC (`10.201.18.50`) sends packet to Jenin Switch (Port `Gi10`).
2. Jenin Switch forwards to default gateway Jenin FortiGate (uplink).
3. Jenin FortiGate (`10.201.18.1`) looks up Tulkarm subnet (`10.165.18.x`).
4. Route via `wan1` (HQ tunnel).
5. Jenin FortiGate sends encrypted traffic from `wan1` (`172.27.13.26`) to HQ FortiGate.
6. HQ FortiGate receives on Port `3`, routes back out Port `3` toward Tulkarm VPN tunnel.
7. Tulkarm FortiGate receives on `wan1`, decrypts, and forwards to internal interface.
8. Tulkarm Switch receives on uplink and delivers to Tulkarm PC (`10.165.18.50`) on Port `Gi10`.

### 8.2 Scenario 12 – Local Branch Printing (Layer 2 Switching)

**Context:** Jenin staff prints to local printer.

**Path Logic:** PC → Switch → Printer (local only).

1. Jenin PC (`10.201.18.50`) sends job to Printer (`10.201.18.55`).
2. PC sees destination is same subnet (`10.201.18.x`).
3. PC sends ARP: “Who has .55?”
4. Jenin Switch forwards frame from User Port (`Gi10`) to Printer Port (`Gi20`).
5. FortiGate gateway and Cisco router are **not** involved.

### 8.3 Scenario 13 – Emergency Outbound Call (WAN Down / SRST)

**Context:** WAN at Jenin is down; user calls an external emergency number.

**Path Logic:** Phone → Local Router → PSTN.

1. Jenin Phone (`10.201.18.102`) detects loss of HQ CUCM.
2. Phone registers to local Cisco Router (`10.201.18.2`) via SRST.
3. User dials external number.
4. Phone sends audio stream to Jenin Switch (Port `Gi1`).
5. Jenin Switch forwards to Cisco Router (`Gi46`).
6. Cisco Router receives on `Gi0/0` and matches dial‑peer 1 (POTS).
7. Router sends call out FXO/ISDN Port (`0/0/0`) to local PSTN provider.

### 8.4 Scenario 14 – HQ Security Viewing Branch Cameras

**Context:** HQ Security views Jenin branch CCTV feed.

**Path Logic:** HQ Admin → HQ Core → WAN → Branch LAN → NVR.

1. HQ Security PC (`172.23.50.100`) sends request to HQ Cisco Core → HQ Fujitsu Core.
2. Fujitsu Core sends to HQ FortiGate (`x1`).
3. HQ FortiGate routes out Port `3` (WAN) to Jenin FortiGate.
4. Jenin FortiGate receives on `wan1` and routes to internal interface.
5. Jenin Switch forwards to NVR on Port `Gi40` (IP `10.201.18.200`).
6. Return path: NVR → Switch → Jenin FG → HQ FG → HQ User.

### 8.5 Scenario 15 – Remote IT Management of Branch Switch

**Context:** Network admin at HQ manages Jenin Switch.

**Path Logic:** Admin → WAN → Branch Switch Management IP.

1. Admin PC (HQ) initiates SSH to `10.201.18.3` (Jenin Switch Mgmt).
2. HQ FortiGate encrypts session and sends via Port `3` tunnel to Jenin.
3. Jenin FortiGate receives on `wan1`, decrypts, and forwards to internal interface.
4. Jenin Switch receives on uplink and recognizes destination IP `.3` as itself.
5. Jenin Switch processes SSH commands and replies back via default gateway Jenin FortiGate (`.1`).

\---

## 9\. Troubleshooting Guide

### 9.1 Scenario A – “The Internet is Down”

1. **Check FortiGate:** Log in to `10.11.12.1`.
2. **Check Interfaces:** Navigate to *Network > Interfaces*. Confirm **Port 2 (WAN)** is **up/green**.
3. **Test Connectivity:** From FortiGate CLI, run `execute ping 8.8.8.8`.

   * If ping **fails**: Problem is likely with ISP.
   * If ping **works**: Problem is likely internal (for example, LAN interface `x1`).

### 9.2 Scenario B – “I Cannot Connect to the Shared Folder / Email”

1. **Check User Connectivity:** Can the user ping the gateway (`172.23.xx.4`)?
2. **Check Cisco FTD Firewall:** As the “Vault Guard,” it may be blocking traffic.

   * Action: Review FTD logs for **deny** messages from user IP to server IP (`172.23.71.x`).
3. **Check Server State:** Verify VM `EXCHANGESRV1` is powered on in vCenter.

### 9.3 Scenario C – “A Specific Floor Is Offline”

1. **Identify Floor:** For example, Floor 4.
2. **Check Cisco Core:** Log in to `172.23.70.254`.
3. **Check Port Mapping:** From Section **5.2**, Floor 4 is `Twe 1/0/4`.
4. **Run Command:** `show interface Twe1/0/4 status`.

   * If status is **notconnect**: Fiber to that floor is broken or unplugged.

### 9.4 Scenario D – “Redundancy Alert” (Current Critical Issue)

* **Problem:** Alerts show `Fujitsu Switch 1 Down` or `Cisco Stack Port 1 Down`.
* **Meaning:** Network is running on reduced redundancy (“spare tire”). A second failure could be catastrophic.

**Action:**

1. Contact vendor for replacement Fujitsu switch.
2. Go to server room and check black stacking cable on back of Cisco Core Switch; reseat it firmly.

## Cable Color Code Standard

## 1.1 Cable Color Standards (Visual Guide)

To identify cables in the rack, follow this color code:

* **ORANGE:** High-Speed Fiber Optic (10G/40G). Used for Core Uplinks and SAN Storage.
* **GREEN:** Copper Ethernet (1G). Used for Management ports, F5 WAF, and Access Layer.
* **BLUE:** WAN Connections. Used for Internet and Branch routers.

\---

## 5\. Master Connection Matrix

### 5.1 The Fiber Backbone (Orange Cables)

|Source Device|Interface|Destination|Interface|Type|
|-|-|-|-|-|
|**Fujitsu Core**|`0/44`|**Cisco Core**|`Po44`|**40G QSFP Fiber**|
|**Fujitsu Core**|`0/1-18`|**ESXi Cluster**|*NICs*|**10G SFP+ Fiber**|
|**Fujitsu Core**|`0/47, 40`|**FortiGate**|`x1, x2`|**10G SFP+ Fiber**|
|**SAN Switch**|`All Ports`|**Storage/Servers**|*HBA*|**16G/32G Fiber**|

### 5.2 The Copper Connections (Green Cables)

|Source Device|Interface|Destination|Interface|Type|
|-|-|-|-|-|
|**Cisco Core**|`Twe 1/0/12`|**F5 WAF**|`Port 1.1`|**1G Copper (GLC-TE)**|
|**Cisco Core**|`Twe 2/0/12`|**F5 WAF**|`Port 1.2`|**1G Copper (GLC-TE)**|
|**Fujitsu Core**|`0/34`|**Cisco FTD**|`Mgmt`|**1G Copper**|
|**Fujitsu Core**|`0/33`|**SAN Switch**|`Mgmt`|**1G Copper**|

\---

*End of Ministry Network Operations Manual – Version 3.0*

