---
id: "MNE-TB-EMAIL-FLOW"
title: "tb-email-flow-failure"
type: "troubleshooting_guide"
status: "active"
owner: "SysAdmin-Team"
criticality: "critical"
environment: "production"
last_review: "2026-07-24"
tags:
  - ministry/operations/troubleshooting
---

# tb-email-flow-failure

Context: [[index-troubleshooting]] | Target: [[exch-srv-01]]

## Diagnostic Flowchart
1. Verify DNS Autodiscover resolution: [[dns-zone-mne-gov-ps]]
2. Test F5 HTTPS VIP reachability: [[f5-vip-public-98]]
3. Check FortiGate policy pass-through: [[fw-fortigate-hq-01]]
4. Verify AD Domain Controller health: [[ad-dc-01]]
5. Check Fujitsu SAN LUN space: [[san-fujitsu-eternus-01]]
