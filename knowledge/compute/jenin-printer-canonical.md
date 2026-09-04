---
id: "prt-jenin-office-01"
name: "Jenin Office Network Printer (HP LaserJet Enterprise)"
category: "compute"
aliases: ["jenin-printer", "printer-jenin", "10.201.18.220", "prt-jenin"]
hostname: "prt-jenin-office-01"
fqdn: "prt-jenin-office-01.mne.gov.ps"
ip: "10.201.18.220"
vlan: "18"
services: ["network-printing", "ipp", "raw-jetdirect-9100", "snmp"]
owner: "Jenin Administrative Support"
related_entities: ["sw-cisco-jenin-01", "fw-fortigate-jenin-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Jenin Office Network Printer

> **Entity ID:** `prt-jenin-office-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🖨️ Printer & Network Specs
- **Hostname:** `prt-jenin-office-01`
- **IP Address:** `10.201.18.220`
- **Product:** HP LaserJet Enterprise M608dn
- **Port:** `9100/tcp` (Raw JetDirect), `631/tcp` (IPP)
- **Subnet:** Jenin Branch Office Subnet `10.201.18.0/24` (Default Gateway: `10.201.18.1`)

