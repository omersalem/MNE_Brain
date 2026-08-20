---
id: "app-auction-test-01"
name: "Auction Portal Web Test Host"
category: "compute"
aliases: ["auction-app", "auct-vs", "172.23.79.100", "auction-test"]
hostname: "app-auction-test-01"
fqdn: "auction.mne.gov.ps"
ip: "172.23.79.100"
vlan: "79"
services: ["http-80", "php-health-check", "auction-portal"]
owner: "E-Government Applications Team"
related_entities: ["waf-f5-bigip-mgmt", "vc-vmware-mgmt-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Auction Portal Web Test Host

> **Entity ID:** `app-auction-test-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🏷️ Application Specs
- **Hostname:** `app-auction-test-01`
- **Backend IP:** `172.23.79.100`
- **Port:** `80/tcp`
- **F5 Virtual Server:** `Auct_VS` (`172.23.10.60:443`)
- **F5 Pool:** `Aucto_Pool`
- **Monitor:** `PHP_Health`
- **WAF Policy:** `asm_auto_l7_policy__Auct_VS`
