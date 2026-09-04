---
id: "waf-f5-bigip-01"
name: "F5 BIG-IP r2000 Web Application Firewall & ADC"
category: "network"
aliases: ["f5-bigip", "waf-f5", "load-balancer", "172.23.70.89", "f5-waf", "f5-bigip-hq-01"]
hostname: "f5-bigip-hq-01"
fqdn: "f5-bigip-hq-01.mne.gov.ps"
ip: "172.23.70.89"
vlan: "70"
services: ["waf-protection", "load-balancing", "ssl-offloading", "asm-policy", "esadad-publishing"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-hq-01", "sw-cisco-core-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — F5 BIG-IP Web Application Firewall & ADC

> **Entity ID:** `waf-f5-bigip-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🛡️ Web Application Firewall Details
- **Hostname:** `f5-bigip-hq-01`
- **Management IP:** `172.23.70.89` (VLAN 70 Network Management)
- **Product:** F5 BIG-IP r2000 Appliance (TMOS v17.5.1.3)
- **Role:** Web Application Firewall for ESADAD public portal (SQLi, XSS, bot protection), SSL offloading
- **Trunk Connectivity:** Cisco Core Ports `Twe 1/0/12` (port 1.1) and `Twe 2/0/12` (port 1.2)

