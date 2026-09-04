---
id: "san-fujitsu-01"
name: "Fujitsu Eternus SAN Storage"
category: "storage"
aliases: ["san", "san-storage", "eternus-san", "172.23.68.20", "san-fujitsu-eternus-01"]
hostname: "san-fujitsu-eternus-01"
fqdn: "san01.mne.gov.ps"
ip: "172.23.68.20"
vlan: "68"
services: ["iscsi", "fibre-channel", "san-storage"]
owner: "Storage Operations Team"
related_entities: ["vc-vmware-hq-01", "backup-veeam-hq-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Fujitsu Eternus SAN Storage

> **Entity ID:** `san-fujitsu-01`  
> **Trust Level:** Level 3 (Canonical Vault Fact)  
> **Last Verified:** 2026-07-30T10:00:00Z  

---

## 🏛️ Storage Array Identity Details
- **Hostname:** `san-fujitsu-eternus-01`
- **Management IP:** `172.23.68.20`
- **Model:** Fujitsu ETERNUS DX200 S5
- **Role:** High-Performance Tier SAN Storage
- **Fabric Connectivity:** Dual Fibre Channel links to Fujitsu Core Switches (172.23.70.70 & 172.23.70.71)

