# Ministry Network Topology – Knowledge Base
**Manual Version:** 3.0 (December 2025)

---

## 1. Network Overview (The Big Picture)

The Ministry network is modeled like a secured office building:

| Device | Model | Mgmt IP | Role |
|---|---|---|---|
| **MNE-CoreSw2** (Fujitsu Core) | Fujitsu Switch | `172.23.70.71` | Central fabric — interconnects all zones (firewalls, campus, servers) |
| **FG-MNE-B** (FortiGate) | FortiGate 601E | `10.11.12.1` (also `172.23.70.4`) | Internet edge & user gateway. Default gateway for staff VLANs, WAN/branch links |
| **Cisco FTD** | Cisco Firepower 3105 | `172.23.70.78` | Server-side firewall — deep inspection, guards VLAN 71/75/79 etc. |
| **F5 WAF** | F5 BIG-IP r2000 | `172.23.70.89` | Web Application Firewall for ESADAD public portal (SQLi, XSS, bot protection) |
| **CoreSwitch1** (Cisco Core) | Cisco 9500 Stack | `172.23.70.254` | Campus aggregation — connects Basement through Floor 6, uplinks to Fujitsu via 40G |

---

## 2. Physical Connections (Cabling)

### 2A. Fiber Backbone (Orange Cables – 10G/40G)

| Source | Port | Destination | Port | Speed | Purpose |
|---|---|---|---|---|---|
| Fujitsu Core | `0/47` | FortiGate | `x1` | 10G SFP+ | User LAN trunk (VLANs 19–26, 42, 76) |
| Fujitsu Core | `0/40` | FortiGate | `x2` | 10G SFP+ | Transit link – server-bound traffic (VLAN 200) |
| Fujitsu Core | `0/39` | Cisco FTD | `Po1 (Outside)` | 10G SFP+ | Traffic entering server zone |
| Fujitsu Core | `0/46` | Cisco FTD | `Po2 (Inside)` | 10G SFP+ | Traffic exiting to server VLANs |
| Fujitsu Core | `0/44` | Cisco Core | `Po44` | 40G QSFP | Campus uplink (all floor traffic) |
| Fujitsu Core | `0/1–18` | ESXi Cluster | NICs | 10G SFP+ | Server data – VM traffic |
| Fujitsu Core | `0/34` | Cisco FTD | `Mgmt 1/1` | 1G Copper | OOB management (VLAN 70) |
| Fujitsu Core | `0/33` | SAN Switch | `Eth0` | 1G Copper | SAN management |

### 2B. Copper Connections (Green Cables – 1G)

| Source | Port | Destination | Port | Purpose |
|---|---|---|---|---|
| Cisco Core | `Twe 1/0/12` | F5 WAF | `1.1` | WAF trunk – VLAN 9 & 10 |
| Cisco Core | `Twe 2/0/12` | F5 WAF | `1.2` | WAF trunk – redundant |

### 2C. FortiGate Ports

| Interface | Connected To | Purpose |
|---|---|---|
| `Port 2` (WAN Primary) | ISP Router | Main Internet (default route) |
| `Port 1` (WAN Legacy) | Legacy ISP / Gov VPN | Backup / other ministries |
| `Port 3` (WAN Branch) | Branch MPLS Router | All 13 branch offices |
| `x1` (LAN Trunk) | Fujitsu `0/47` | All user VLANs |
| `x2` (Transit) | Fujitsu `0/40` | Server-bound traffic |
| `ha` | Secondary FortiGate | HA heartbeat/sync |

### 2D. Campus Floor Ports (Cisco Core Downlinks)

| Cisco Core Port | Device | IP | Location |
|---|---|---|---|
| `Twe 1/0/1` | Switch F1 | `172.23.70.222` | Floor 1 |
| `Twe 1/0/3` | Switch F2 | `172.23.70.223` | Floor 2 |
| `Twe 1/0/2` | Switch F3 | `172.23.70.224` | Floor 3 |
| `Twe 1/0/4` | Switch F4 | `172.23.70.225` | Floor 4 |
| `Twe 1/0/5` | Switch F5 | `172.23.70.226` | Floor 5 |
| `Twe 1/0/6` | Switch F6 | `172.23.70.227` | Floor 6 |
| `Twe 1/0/9` | Switch F0 | `172.23.70.221` | Ground Floor |
| `Twe 1/0/7` | Switch F_-1 | `172.23.70.220` | Basement Staff |
| `Twe 1/0/8` | Switch Khadamat | `172.23.70.219` | Basement Services |
| `Twe 2/0/6` | DMZ Switch | `172.23.9.254` | Legacy DMZ |
| `Twe 2/0/10` | CUCM Server | `172.23.76.11` | Call Manager |
| `Twe 2/0/11` | VoIP Router | `172.23.76.2` | Voice Gateway |

---

## 3. VLAN Map

| VLAN | Name / Purpose | Subnet |
|---|---|---|
| 19–26 | Staff floor VLANs | `172.23.19–26.x` |
| 30 | Development & Testing | `172.23.30.x` |
| 42 | Printers | `172.23.42.x` |
| 50 | Admin / IT Management | `172.23.50.x` |
| 55 | MIND UXP | `172.23.55.x` |
| 69 | VMware Management | `172.23.69.x` |
| 70 | Network Device Management | `172.23.70.x` |
| 71 | Core Application Servers | `172.23.71.x` |
| 72 | Trade | `172.23.72.x` |
| 74 | ERCompany | `172.23.74.x` |
| 75 | Database Servers | `172.23.75.x` |
| 76 | VoIP | `172.23.76.x` |
| 78 | Application | `172.23.78.x` |
