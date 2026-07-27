---
id: MNE-VCENTER-MAIN
title: vCenter Server Appliance (vcenter-main)
type: vcenter_server
status: live_verified
vendor: VMware
model: VMware VirtualCenter 7.0.3 build-23788036
os: VMware Photon OS 3.0 (Build 05f9d3d8d)
site: HQ
owner: SysAdmin-Team
criticality: critical
environment: production
last_review: '2026-07-27'
tags:
- ministry/vmware/vcenter
- ministry/site/hq
aliases:
- MNE-VCENTER-MAIN
- vcenter-main
- vcenter.mne.gov.ps
source: Live Verification
trust_tier: 5
last_verified: '2026-07-27'
related_entities: []
---
# vCenter Server Appliance (vcenter-main)

Context: [[index-vmware]] | Site: [[site-hq]]

## System Details
- **Management IP:** `172.23.69.38` (SSH Port 22)
- **Appliance FQDN:** `vcenter.mne.gov.ps`
- **OS Platform:** VMware Photon OS 3.0 (Build `05f9d3d8d`)
- **Appliance Version:** VMware VirtualCenter `7.0.3 build-23788036`
- **Uptime:** 274 days (Live Verified 2026-07-27)
- **Live Status:** UP / Verified

## Critical Storage Health & Alerts
- ⚠️ **`/storage/archive` Alert:** **95% Used** (89 GB / 98 GB used, only 4.8 GB free). Contains archived support bundles and audit logs.
- **`/storage/log`:** 20% Used (4.6 GB / 25 GB)
- **`/` (Root):** 25% Used (11 GB / 47 GB)
- **`/storage/db`:** 4% Used (769 MB / 25 GB)

## Managed Compute & ESXi
- [[esxi-host-01]]

## Verified Telemetry & Evidence
- **Evidence Record:** [compute-live-vcenter-main-1785145838.json](file:///D:/projects/MNE_Brain/MNE_Brain/operations/evidence/compute-live-vcenter-main-1785145838.json)
- **Raw Telemetry Output:** [live-vcenter-main-1785145838-raw.txt](file:///D:/projects/MNE_Brain/MNE_Brain/operations/evidence/live-vcenter-main-1785145838-raw.txt)

