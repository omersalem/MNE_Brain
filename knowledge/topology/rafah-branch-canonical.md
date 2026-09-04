---
id: "fw-fortigate-rafah-01"
name: "Rafah Regional Branch Firewall (FortiGate)"
category: "network"
aliases: ["rafah-firewall", "fw-rafah", "10.235.18.1", "rafah-branch"]
hostname: "fw-fortigate-rafah-01"
fqdn: "fw-fortigate-rafah-01.mne.gov.ps"
ip: "10.235.18.1"
vlan: "18"
services: ["firewall", "ipsec-vpn", "branch-routing", "nat"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-hq-01", "sw-cisco-rafah-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Rafah Regional Branch Firewall (FortiGate)

> **Entity ID:** `fw-fortigate-rafah-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🛡️ Rafah Branch Security Details
- **Hostname:** `fw-fortigate-rafah-01`
- **Gateway IP:** `10.235.18.1`
- **Subnet:** `10.235.18.0/24` (Rafah Regional Directorate)
- **Switch IP:** `10.235.18.2` (sw-cisco-rafah-01)
- **IPSec Tunnel:** Connected to HQ FortiGate (`172.23.70.4` / `172.23.13.201`) via WAN
