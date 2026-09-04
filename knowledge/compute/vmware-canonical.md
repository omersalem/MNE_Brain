---
id: "vc-vmware-hq-01"
name: "vCenter Server Appliance (VCSA 7.0.3)"
category: "compute"
aliases: ["vmware", "vcenter", "vcenter-hq", "vcenter-main", "172.23.69.38"]
hostname: "vcenter-main"
fqdn: "vcenter-main.mne.gov.ps"
ip: "172.23.69.38"
vlan: "69"
services: ["vcenter", "esxi-management", "vsphere", "vm-clustering"]
owner: "Virtualization Infrastructure Team"
related_entities: ["fw-fortigate-hq-01", "san-fujitsu-01", "esxi-node-hq-01", "esxi-node-hq-02"]
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
- **Hostname:** `vcenter-main`
- **Management IP:** `172.23.69.38` (VLAN 69 VMware Management)
- **Product:** VMware vCenter Server Appliance 7.0 Update 3
- **Datacenter:** HQ-Datacenter
- **Cluster:** HQ-Production-Cluster

