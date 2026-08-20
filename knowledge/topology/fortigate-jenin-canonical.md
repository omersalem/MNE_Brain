---
id: "fw-fortigate-jenin-01"
name: "Jenin Branch Firewall (FortiGate)"
category: "network"
aliases: ["jenin-firewall", "fw-jenin", "fortigate-jenin", "172.23.20.1", "jenin-fw"]
hostname: "fw-fortigate-jenin-01"
fqdn: "fw-fortigate-jenin-01.mne.gov.ps"
ip: "172.23.20.1"
vlan: "20"
services: ["firewall", "ipsec-vpn", "nat", "branch-routing"]
owner: "Network & Security Operations Team"
related_entities: ["sw-cisco-jenin-01", "fw-fortigate-hq-01", "prt-jenin-office-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Jenin Branch Firewall (FortiGate)

> **Entity ID:** `fw-fortigate-jenin-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🛡️ Device & Network Specs
- **Hostname:** `fw-fortigate-jenin-01`
- **Management IP:** `172.23.20.1`
- **Product:** FortiGate 60F UTM Appliance
- **Branch Location:** Jenin Branch Office (Subnet `172.23.20.0/24`)
- **IPSec Tunnel:** Connected to HQ Core Firewall (`172.23.19.1`) over WAN
