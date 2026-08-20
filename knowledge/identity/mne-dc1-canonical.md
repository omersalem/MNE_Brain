---
id: "dc-mne-ad-01"
name: "MNE-DC1 Primary Domain Controller & Enterprise DNS"
category: "identity"
aliases: ["mne-dc1", "mne-dc1-ad", "172.23.71.27", "172.23.71.173", "dc1-mne"]
hostname: "dc-mne-ad-01"
fqdn: "MNE-DC1.mne.gov.ps"
ip: "172.23.71.27"
vlan: "71"
services: ["active-directory", "primary-dns", "winrm", "kerberos", "ldap-ssl"]
owner: "Identity & Core Windows Infrastructure Team"
related_entities: ["ex-windows-mail-01", "dc-windows-ad-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — MNE-DC1 Primary Domain Controller & Enterprise DNS

> **Entity ID:** `dc-mne-ad-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🔑 Enterprise Directory & DNS Details
- **Hostname:** `MNE-DC1`
- **Primary IP:** `172.23.71.27`
- **Secondary IP:** `172.23.71.173`
- **Domain:** `mne.gov.ps`
- **WinRM Port:** `5985/tcp` (Username: `MNE_AD_USERNAME`)
- **DNS Zones Hosted:** `mne.gov.ps`, `71.23.172.in-addr.arpa`, `70.23.172.in-addr.arpa`
