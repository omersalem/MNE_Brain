# Ministry of National Economy — VLAN & IP Subnet Assignment Matrix

This document defines the complete VLAN mapping and IP addressing scheme for the Ministry of National Economy (MNE) Headquarters and branch networks.

---

## VLAN Subnet Map

| VLAN ID | Subnet Range | Name/Purpose | Gateway | Primary Devices & Allocation |
|---|---|---|---|---|
| **1** | `172.23.1.0/24` | Default VLAN | `172.23.1.254` | Unassigned ports (should be disabled for security). |
| **19** | `172.23.19.0/24` | Staff Floor 1 | `172.23.19.254` | Workstations and thin clients on Floor 1. |
| **21** | `172.23.21.0/24` | Staff Floor 2 | `172.23.21.254` | Workstations and thin clients on Floor 2. |
| **23** | `172.23.23.0/24` | Staff Floor 3 | `172.23.23.254` | Workstations and thin clients on Floor 3. |
| **30** | `172.23.30.0/24` | Dev & Testing | `172.23.30.254` | Software developers, sandboxed sandbox systems. |
| **42** | `172.23.42.0/24` | Printers Network | `172.23.42.254` | Legacy network printers. |
| **50** | `172.23.50.0/24` | IT & Admin Mgmt | `172.23.50.254` | IT team workstations, local management terminals. |
| **55** | `172.23.55.0/24` | MIND UXP | `172.23.55.254` | Ministry UXP Adapters and integration servers. |
| **69** | `172.23.69.0/24` | VMware Management | `172.23.69.254` | ESXi hypervisors, vCenter Server, SAN iSCSI interfaces. |
| **70** | `172.23.70.0/24` | Network Mgmt | `172.23.70.254` | FortiGate (`172.23.70.4`), Switch (`172.23.70.71`), FMC (`172.23.70.77`). |
| **71** | `172.23.71.0/24` | Core App Servers | `172.23.71.254` | MNE-DC1 (`.27`), MNE-DC2 (`.28`), MYQ (`.71`), SCCM (`.84`), EXCHANGESRV1 (`.35`). |
| **75** | `172.23.75.0/24` | Database Servers | `172.23.75.254` | Manus-Srv (`.200`), primary SQL clusters. |
| **79** | `172.23.79.0/24` | DMZ / Public Web | `172.23.79.254` | ESADAD (`.77`), procedures-srv (`.79`). |
| **90** | `172.23.90.0/24` | Printers (Core) | `172.23.90.254` | Dedicated subnet for all new network printers. |
| **100** | `172.23.100.0/24`| WiFi Infrastructure| `172.23.100.254`| Access Points, Wireless LAN Controllers (WLC). |
| **102** | `172.23.102.0/24`| Nablus Branch | `172.23.102.254`| Branch router WAN interfaces, local employee PCs. |

---

## Inter-VLAN Routing Policy
- All routing between VLANs is performed by the core firewall cluster (FG-MNE-B) acting as the default gateway (`.254`) for all subnets except network management.
- Access to the Database Server VLAN (VLAN 75) is strictly limited to Application Servers (VLAN 71) on database ports (TCP 1433 for SQL Server, TCP 1521 for Oracle).
- Network Management (VLAN 70) is only accessible from the IT management subnet (VLAN 50).
