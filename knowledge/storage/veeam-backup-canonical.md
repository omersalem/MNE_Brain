---
id: "backup-veeam-hq-01"
name: "HQ Veeam Backup & Disaster Recovery Server"
category: "storage"
aliases: ["veeam-backup", "backup-server", "veeam-hq", "172.23.19.60"]
hostname: "backup-veeam-hq-01"
fqdn: "backup-veeam-hq-01.mne.gov.ps"
ip: "172.23.19.60"
vlan: "19"
services: ["veeam-backup", "vm-snapshots", "disaster-recovery", "san-repository"]
owner: "Storage & Disaster Recovery Team"
related_entities: ["san-fujitsu-01", "vc-vmware-hq-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — HQ Veeam Backup & Disaster Recovery Server

> **Entity ID:** `backup-veeam-hq-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 💾 Disaster Recovery & Backup Specs
- **Hostname:** `backup-veeam-hq-01`
- **Management IP:** `172.23.19.60`
- **Product:** Veeam Backup & Replication v12 Enterprise Plus
- **Target Storage:** Fujitsu Eternus SAN Storage (`172.23.19.50`)
