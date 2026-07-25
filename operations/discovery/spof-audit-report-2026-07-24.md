---
id: "MNE-RPT-SPOF-AUDIT-2026-07-24"
title: "End-to-End Traffic Path & Single Point of Failure (SPOF) Audit"
type: "infrastructure_audit"
status: "completed"
owner: "Lead-Architect"
execution_date: "2026-07-24"
tags:
  - ministry/audit/spof
  - ministry/traffic-path
---

# End-to-End Traffic Path & Single Point of Failure (SPOF) Audit

Context: [[master-dashboard]] | Parent: [[index-operations]]

## 🏛️ Executive Summary
This document provides a comprehensive end-to-end traffic path analysis and Single Point of Failure (SPOF) assessment across all physical, virtual, security, and storage tiers of the Ministry Infrastructure Digital Twin.

---

## 🛣️ Path 1: ESADAD Public Portal & Greenunit ABRS Web Service
```
[External User]
      │ (Port 443 / HTTPS)
      ▼
[FortiGate FG-MNE-B (172.23.70.4)] ──> Policy 104 Pass-Through
      │
      ▼
[F5 BIG-IP r2000 WAF (172.23.70.89 / VIP: 172.23.79.200)] ──> WAF Security Inspection
      │
      ▼
[Cisco FTD-01 (172.23.70.78)] ──> Deep Packet Server Inspection (VLAN 79)
      │
      ▼
[Fujitsu Core MNE-CoreSw2 (172.23.70.71)] ──> Inter-VLAN Routing
      │
      ▼
[ESXi Host 01 (172.23.69.41)] ──> VM Container [[srv-linux-abrs-01]]
      │
      ▼
[Greenunit ABRS (172.23.79.200)] ──> Nginx + PHP 8.3 + MariaDB
      │
      ▼
[Primary SQL DB MNEPDB-SRV (172.23.71.73)] ──> Core Data Storage
      │
      ▼
[Fujitsu SAN ETERNUS DX200 (172.23.68.20)] ──> VMFS Volume [[VMware-DS]]
```

### 🔴 SPOFs & Risk Exposure (Path 1)
1. **Single Public VIP Endpoint (`172.23.79.200`):** Single F5 VIP instance. Loss of F5 WAF appliance halts external portal access.
2. **Single Database Node (`MNEPDB-SRV` - `172.23.71.73`):** Primary SQL database has no active secondary replica listed in inventory.
3. **Single Hypervisor Host (`ESXi Host 01`):** ABRS VM and Database VM run on the same ESXi host. Physical host failure drops both web frontend and database backend.

---

## 🛣️ Path 2: Enterprise Email & OWA Flow (Exchange 2019)
```
[Outlook / OWA Client]
      │
      ▼
[DNS Zone mne.gov.ps (172.23.71.27)] ──> Resolves mail.mne.gov.ps & autodiscover
      │
      ▼
[FortiGate FG-MNE-B (172.23.70.4)] ──> SSL-VPN Portal / Perimeter Pass-Through
      │
      ▼
[F5 BIG-IP WAF (172.23.70.89)] ──> SSL Offloading & Reverse Proxy
      │
      ▼
[Exchange DAG Pair (EXCHANGESRV1: 172.23.71.35 / EXCHANGESRV2: 172.23.71.36)]
      │
      ├──> Active Directory Auth: [[ad-dc-01]] (172.23.71.27) / [[ad-dc-02]] (172.23.71.28)
      └──> Storage: [[san-fujitsu-eternus-01]] LUN Datastore [[VMware-DS]]
```

### 🔴 SPOFs & Risk Exposure (Path 2)
1. **Exchange High Availability Status:** **EXCELLENT (Low Risk)** — Protected by 2-node DAG (`EXCHANGESRV1` + `EXCHANGESRV2`) and dual DCs (`MNE-DC1` + `MNE-DC2`).
2. **Single SAN Array Bottleneck:** Both Exchange EDB databases sit on the single Fujitsu ETERNUS DX200 array (`172.23.68.20`). SAN controller or array loss freezes mailbox access.

---

## 🛣️ Path 3: Branch-to-HQ Site Interconnect (11 Branches)
```
[Branch Client Workstation]
      │
      ▼
[Branch Access Switch (10.x.18.3)] ──> Local VLAN Access
      │
      ▼
[Branch FortiGate Firewall (10.x.18.1)] ──> Site-to-Site IPSec Tunnel
      │
      ▼
[HQ Central Branch Transit Link (172.23.13.200/30)]
      │
      ▼
[FortiGate HQ FG-MNE-B (172.23.70.4 - Port 3 Gateway: 172.23.13.201)]
      │
      ▼
[Fujitsu Core MNE-CoreSw2 (172.23.70.71)] ──> Core Services VLAN 71
      │
      ▼
[Active Directory MNE-DC1 (172.23.71.27)] ──> Domain Auth & Policy
```

### 🔴 SPOFs & Risk Exposure (Path 3)
1. **Single Central Aggregation Interface (`port3`):** All 11 branch IPSec tunnels aggregate through a single physical interface (`port3`) on FortiGate HQ. Physical link cut isolates all 11 branches simultaneously.
2. **Jericho Branch Outage:** Jericho Branch (`10.211.18.1`) is currently unreachable due to external WAN/power loss.

---

## 🛣️ Path 4: Veeam Backup & Disaster Recovery Architecture
```
[Production Workloads (148 VMs)]
      │
      ▼
[vCenter Appliance (172.23.69.38)] ──> vSphere Storage API / Changed Block Tracking (CBT)
      │
      ▼
[Standalone Veeam Backup Server (FUJI-BACKUP-SER: 172.23.69.60)]
      │
      ▼
[NFS Backup Storage Target (VeeamBackup_FUJI-BACKUP-SER: 959.64 GB NFS)]
```

### 🔴 SPOFs & Risk Exposure (Path 4)
1. **Workgroup Standalone Vulnerability:** `FUJI-BACKUP-SER` runs in `WORKGROUP` (non-domain joined). While secure against AD compromise, credentials must be manually managed.
2. **Backup Storage Capacity Pressure:** The primary NFS backup target has only 959.64 GB total capacity (`957.32 GB` free), which is insufficient for full image-level backups of a 98.96 TB production datastore (`VMware-DS`).

---

## 🛠️ Recommended Remediation Action Plan

| Priority | Targeted Component | Recommended Architectural Action |
| :--- | :--- | :--- |
| **P1 (Critical)** | **FortiGate HQ Branch Aggregation** | Configure 802.3ad Link Aggregation (LACP) across `port3` and `port4` for redundant branch transit paths. |
| **P1 (Critical)** | **F5 BIG-IP WAF** | Deploy an Active-Standby high-availability pair for F5 BIG-IP r2000 to eliminate single VIP point of failure (`172.23.79.200`). |
| **P1 (Critical)** | **VMware Host Placement** | Enable vSphere HA and anti-affinity rules to keep `srv-linux-abrs-01` and `MNEPDB-SRV` on separate physical ESXi hosts. |
| **P2 (High)** | **Veeam Backup Storage** | Provision an off-site secondary SAN or tape repository to scale backup capacity beyond the current 959.64 GB NFS target. |
| **P2 (High)** | **Jericho Branch Connection** | Re-verify WAN ISP link status for `10.211.18.1`. |
