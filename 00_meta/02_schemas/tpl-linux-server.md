---
id: "MNE-TMPL-LINUX-SRV"
title: "Linux Server Template"
type: "linux_server"
status: "active"
vendor: "Canonical / RedHat"
os: "Ubuntu 22.04 LTS / RHEL 9"
site: "HQ"
owner: "SysAdmin-Team"
criticality: "medium"
environment: "production"
last_review: "YYYY-MM-DD"
tags:
  - ministry/compute/linux
---

# {{title}}

Context: [[index-linux]] | Host: [[esxi-host-01]]

## System Information
- **Management IP:** 
- **Active Services:** Nginx, PHP-FPM, MariaDB

## Dependencies
- **VMware Host:** [[esxi-host-01]]
- **SAN Storage:** [[san-fujitsu-eternus-01]]
