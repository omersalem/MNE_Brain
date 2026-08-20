---
id: "fmc-cisco-hq-01"
name: "Cisco Firepower Management Center (FMC)"
category: "network"
aliases: ["cisco-fmc", "fmc-hq", "firepower-mgmt", "172.23.70.77"]
hostname: "fmc-cisco-hq-01"
fqdn: "fmc-cisco-hq-01.mne.gov.ps"
ip: "172.23.70.77"
vlan: "70"
services: ["fmc-management", "ips-sensor-mgmt", "firepower-policy"]
owner: "Network & Security Operations Team"
related_entities: ["ftd-cisco-hq-01", "fw-fortigate-edge-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Cisco Firepower Management Center (FMC)

> **Entity ID:** `fmc-cisco-hq-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🛡️ Security Appliance Details
- **Hostname:** `fmc-cisco-hq-01`
- **Management IP:** `172.23.70.77`
- **Product:** Cisco Firepower Management Center Virtual Appliance
- **SSH Port:** `22/tcp` (Username: `MNE_FMC_USERNAME`)
- **Role:** Centralized management and security policy deployment for internal FTD firewalls.
