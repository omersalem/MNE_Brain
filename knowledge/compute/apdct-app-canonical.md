---
id: "app-apdct-web-01"
name: "APDCT Government Application Server"
category: "compute"
aliases: ["apdct", "apdct-app", "172.23.79.79", "apdct-web"]
hostname: "app-apdct-web-01"
fqdn: "apdct.mne.gov.ps"
ip: "172.23.79.79"
vlan: "79"
services: ["http-80", "apdct-service", "internal-portal"]
owner: "E-Government Applications Team"
related_entities: ["waf-f5-bigip-mgmt", "vc-vmware-mgmt-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — APDCT Government Application Server

> **Entity ID:** `app-apdct-web-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 📱 Application Details
- **Hostname:** `app-apdct-web-01`
- **Backend IP:** `172.23.79.79`
- **Port:** `80/tcp`
- **F5 VIP Target:** `APDCT_https` (`172.23.10.79:443`)
- **F5 Pool:** `APDCT_Pool`
- **WAF Policy:** `asm_auto_l7_policy__APDCT_https`
