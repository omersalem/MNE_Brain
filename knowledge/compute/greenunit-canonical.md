---
id: "web-greenunit-ubuntu-01"
name: "Greenunit Web Application Host (Ubuntu Nginx/PHP)"
category: "compute"
aliases: ["greenunit", "web-greenunit", "ubuntu-greenunit", "172.23.79.200"]
hostname: "web-greenunit-ubuntu-01"
fqdn: "greenunit.mne.gov.ps"
ip: "172.23.79.200"
vlan: "79"
services: ["nginx-80", "php8.3-fpm", "mariadb-3306", "ssh-22", "fail2ban"]
owner: "Web Applications & E-Government Operations Team"
related_entities: ["waf-f5-bigip-mgmt", "vc-vmware-mgmt-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Greenunit Web Application Host (Ubuntu Nginx/PHP)

> **Entity ID:** `web-greenunit-ubuntu-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🌐 Application Host Baseline
- **Hostname:** `web-greenunit-ubuntu-01`
- **Management IP:** `172.23.79.200`
- **OS:** Ubuntu 24.04 LTS (Kernel 6.8)
- **Stack:** Nginx 1.24 + PHP 8.3-FPM + MariaDB 10.11
- **SSH Port:** `22/tcp` (Username: `MNE_LINUX_USERNAME`)
- **Published Via F5:** `vs-greenunit-mne-gov-ps` (`172.23.10.98:443`)
