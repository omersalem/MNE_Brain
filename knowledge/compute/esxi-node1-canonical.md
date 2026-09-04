---
id: "esxi-node-hq-01"
name: "HQ ESXi Hypervisor Host Node 01"
category: "compute"
aliases: ["esxi-01", "esxi-hq-01", "172.23.69.30", "host-node-01"]
hostname: "esxi-node-hq-01"
fqdn: "esxi-node-hq-01.mne.gov.ps"
ip: "172.23.69.30"
vlan: "69"
services: ["vmware-esxi", "host-management", "vmotion", "vsan"]
owner: "Virtualization & Infrastructure Team"
related_entities: ["vc-vmware-hq-01", "san-fujitsu-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — HQ ESXi Hypervisor Host Node 01

> **Entity ID:** `esxi-node-hq-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🖥️ Hypervisor Hardware Specs
- **Hostname:** `esxi-node-hq-01`
- **Management IP:** `172.23.69.30` (VLAN 69 VMware Management)
- **Product:** VMware ESXi 7.0 Update 3
- **vCenter Server:** Managed by `vc-vmware-hq-01` (`172.23.69.38`)
- **Network Interfaces:** Dual 10G SFP+ uplinks to Fujitsu Core Switch

