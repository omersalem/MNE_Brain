---
id: "MNE-TMPL-BRANCH"
title: "Branch Template"
type: "site_branch"
status: "draft|active"
owner: "Network-Team"
criticality: "medium"
environment: "production"
last_review: "YYYY-MM-DD"
tags:
  - ministry/site/branch
---

# {{title}}

Context: [[master-dashboard]] | Parent: [[site-hq]]

## Branch Overview
- **Branch Code:** 
- **Location:** 
- **HQ Connection Type:** IPSec VPN / Leased Line

## Network & Security
- **Branch Router:** [[rtr-cisco-wan-01]]
- **Branch Firewall:** [[fw-fortigate-branch-01]]
- **Branch Access Switch:** [[sw-cisco-access-01]]

## Dependencies
- **HQ Identity:** [[ad-dc-01]]
- **HQ DNS:** [[dns-zone-mne-gov-ps]]
