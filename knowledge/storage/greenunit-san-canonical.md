---
id: "san-greenunit-01"
name: "Greenunit SAN Fibre Storage Controller"
category: "storage"
aliases: ["greenunit-san", "san-70", "san-controller", "172.23.70.70"]
hostname: "san-greenunit-01"
fqdn: "san-greenunit-01.mne.gov.ps"
ip: "172.23.70.70"
vlan: "70"
services: ["fibre-channel", "iscsi-target", "san-lun-management"]
owner: "Storage Operations Team"
related_entities: ["san-fujitsu-01", "sw-fujitsu-san-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Greenunit SAN Fibre Storage Controller

> **Entity ID:** `san-greenunit-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 💾 Storage SAN Controller Details
- **Hostname:** `san-greenunit-01`
- **Management IP:** `172.23.70.70`
- **SSH Port:** `22/tcp` (Username: `MNE_SAN_USERNAME`)
- **Capacity:** 120 TB Raw SAS/NVMe Fibre Channel Storage Array
