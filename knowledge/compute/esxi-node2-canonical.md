---
id: "esxi-node-hq-02"
name: "HQ ESXi Hypervisor Host Node 02"
category: "compute"
aliases: ["esxi-02", "esxi-hq-02", "172.23.19.12", "host-node-02"]
hostname: "esxi-node-hq-02"
fqdn: "esxi-node-hq-02.mne.gov.ps"
ip: "172.23.19.12"
vlan: "19"
services: ["vmware-esxi", "host-management", "vmotion", "vsan"]
owner: "Virtualization & Infrastructure Team"
related_entities: ["vc-vmware-hq-01", "san-fujitsu-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — HQ ESXi Hypervisor Host Node 02

> **Entity ID:** `esxi-node-hq-02`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🖥️ Hypervisor Hardware Specs
- **Hostname:** `esxi-node-hq-02`
- **Management IP:** `172.23.19.12`
- **Product:** VMware ESXi 7.0 Update 3 (Dell PowerEdge R750)
- **vCenter Server:** Managed by `vc-vmware-hq-01` (`172.23.19.10`)
- **RAM / CPU:** 512 GB RAM | 64 Cores Intel Xeon Platinum
