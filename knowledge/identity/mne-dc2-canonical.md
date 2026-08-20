---
id: "dc-mne-ad-02"
name: "MNE-DC2 Secondary Domain Controller & Domain Naming Master"
category: "identity"
aliases: ["mne-dc2", "mne-dc2-ad", "172.23.71.28", "dc2-mne"]
hostname: "MNE-DC2"
fqdn: "MNE-DC2.mne.gov.ps"
ip: "172.23.71.28"
vlan: "71"
services: ["active-directory", "dns-replica", "domain-naming-master", "rid-master"]
owner: "Identity & Core Windows Infrastructure Team"
related_entities: ["dc-mne-ad-01", "ex-windows-mail-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — MNE-DC2 Secondary Domain Controller

> **Entity ID:** `dc-mne-ad-02`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🔑 Directory & FSMO Role Details
- **Hostname:** `MNE-DC2`
- **Management IP:** `172.23.71.28`
- **Domain:** `mne.gov.ps`
- **FSMO Roles:** Domain Naming Master, RID Master
