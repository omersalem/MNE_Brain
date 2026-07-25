---
id: "MNE-STD-FRONTMATTER"
title: "YAML Frontmatter Specification"
type: "infrastructure_standard"
status: "active"
owner: "Architecture-Team"
last_review: "2026-07-24"
tags:
  - ministry/standards/frontmatter
---

# YAML Frontmatter Specification

Context: [[master-dashboard]] | Parent: [[index-standards]]

## Mandatory Attributes
Every file in the vault MUST contain:
- `id`: Permanent UUID or formatted unique string (`MNE-...`)
- `title`: Human-readable title
- `type`: Entity type identifier matching canonical schemas
- `status`: `active`, `maintenance`, `draft`, or `archived`
- `owner`: Responsible team (`Network-Team`, `SysAdmin-Team`, `SecOps-Team`)
- `criticality`: `low`, `medium`, `high`, `critical`
- `environment`: `production`, `staging`, `lab`
- `last_review`: Date in `YYYY-MM-DD`
- `tags`: List of hierarchical tags starting with `ministry/`
