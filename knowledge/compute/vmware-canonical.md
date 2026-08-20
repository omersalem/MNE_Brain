---
id: "vc-vmware-hq-01"
name: "vCenter Server HQ"
category: "compute"
aliases: ["vmware", "vcenter", "vcenter-hq", "172.23.19.10"]
hostname: "vc-vmware-hq-01"
fqdn: "vc-vmware-hq-01.mne.gov.ps"
ip: "172.23.19.10"
vlan: "19"
services: ["vcenter", "esxi-management", "vsphere"]
owner: "Virtualization Infrastructure Team"
related_entities: ["fw-fortigate-hq-01", "san-fujitsu-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — vCenter Server HQ

> **Entity ID:** `vc-vmware-hq-01`  
> **Trust Level:** Level 3 (Canonical Vault Fact)  
> **Last Verified:** 2026-07-30T10:00:00Z  

---

## 🏛️ Compute Identity & Host Details
- **Hostname:** `vc-vmware-hq-01`
- **Management IP:** `172.23.19.10`
- **Product:** VMware vCenter Server Appliance 7.0 Update 3
- **Datacenter:** HQ-Datacenter
- **Cluster:** HQ-Production-Cluster
