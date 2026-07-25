---
id: "MNE-STD-NAMING"
title: "Deterministic Naming Conventions"
type: "infrastructure_standard"
status: "active"
owner: "Architecture-Team"
last_review: "2026-07-24"
tags:
  - ministry/standards/naming
---

# Deterministic Naming Conventions

Context: [[master-dashboard]] | Parent: [[index-standards]]

## File Basename Rules
1. All filenames MUST use kebab-case (`lower-case-with-hyphens`).
2. Filenames MUST use functional component prefixes:
   - Sites: `site-`
   - Firewalls: `fw-fortigate-`, `cisco-ftd-`, `cisco-fmc-`
   - Switches: `sw-cisco-core-`, `sw-cisco-access-`
   - Routers: `rtr-cisco-`
   - WAF / Load Balancing: `f5-vip-`, `f5-pool-`
   - Microsoft Services: `ad-dc-`, `dns-zone-`, `dhcp-scope-`, `exch-srv-`, `sccm-srv-`
   - Virtualization: `vcenter-`, `esxi-host-`
   - Storage: `san-fujitsu-`, `fc-sw-fujitsu-`
   - Workloads: `srv-linux-`, `srv-win-`
   - Operations: `sop-`, `rca-`, `tb-`
