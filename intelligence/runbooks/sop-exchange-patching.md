---
id: "MNE-SOP-EXCHANGE-PATCH"
title: "sop-exchange-patching"
type: "sop_runbook"
status: "active"
owner: "SysAdmin-Team"
criticality: "high"
environment: "production"
last_review: "2026-07-24"
tags:
  - ministry/operations/runbook
---

# sop-exchange-patching

Context: [[index-runbooks]] | System: [[exch-srv-01]]

## Execution Steps
1. Put Exchange Mailbox server [[exch-srv-01]] in Maintenance Mode.
2. Verify F5 VIP [[f5-vip-public-98]] health checks redirect traffic.
3. Install Cumulative Update (CU) / Security Update (SU).
4. Reboot host on [[esxi-host-01]] and run diagnostic verification.
