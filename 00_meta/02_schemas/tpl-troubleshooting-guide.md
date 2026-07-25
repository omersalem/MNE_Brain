---
id: "MNE-TMPL-TB"
title: "Troubleshooting Guide Template"
type: "troubleshooting_guide"
status: "active"
owner: "Operations-Team"
criticality: "high"
environment: "production"
last_review: "YYYY-MM-DD"
tags:
  - ministry/operations/troubleshooting
---

# {{title}}

Context: [[index-troubleshooting]]

## Problem Description
- Symptom: User cannot connect to service.

## Diagnostic Flowchart & Traversal Path
1. Check DNS resolution: [[dns-zone-mne-gov-ps]]
2. Check Firewall policy: [[fw-fortigate-hq-01]]
3. Check Server health: [[exch-srv-01]]
