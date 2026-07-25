---
id: "MNE-STD-TAGS"
title: "Vault Tagging Strategy"
type: "infrastructure_standard"
status: "active"
owner: "Architecture-Team"
last_review: "2026-07-24"
tags:
  - ministry/standards/tagging
---

# Ministry Knowledge Base Tagging Strategy

Context: [[master-dashboard]] | Parent: [[index-standards]]

## Tag Hierarchy Principles
To maintain a clean graph and prevent tag bloat, all vault tags MUST use hierarchical slashes starting with `ministry/`:

- `ministry/site` (HQ, Branches)
- `ministry/security` (`fortigate`, `f5-waf`, `cisco-fmc`, `cisco-ftd`)
- `ministry/cisco` (`core-switch`, `access-switch`, `router`)
- `ministry/microsoft` (`active-directory`, `dns`, `dhcp`, `sccm`, `exchange`)
- `ministry/vmware` (`vcenter`, `esxi`)
- `ministry/storage` (`fujitsu-san`, `fc-switch`)
- `ministry/compute` (`windows`, `linux`, `abrs`)
- `ministry/operations` (`runbook`, `incident`, `troubleshooting`)
- `ministry/projects`
- `ministry/standards`
