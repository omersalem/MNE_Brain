---
id: "MNE-TMPL-CISCO-CORE"
title: "Cisco Core Switch Template"
type: "cisco_core_switch"
status: "active"
vendor: "Cisco"
model: "Catalyst 9500"
os: "Cisco IOS-XE"
site: "HQ"
owner: "Network-Team"
criticality: "critical"
environment: "production"
last_review: "YYYY-MM-DD"
tags:
  - ministry/cisco/core-switch
---

# {{title}}

Context: [[index-network-and-security]] | Site: [[site-hq]]

## Overview & Interconnects
- **Management IP:** 
- **VLAN Gateway Services:** Inter-VLAN Routing Enabled

## Connected Infrastructure
- **Upstream Firewall:** [[fw-fortigate-hq-01]]
- **Downstream Access Switches:** [[sw-cisco-access-01]]
- **VMware ESXi Host Trunks:** [[esxi-host-01]]
- **F5 WAF Interconnect:** [[f5-vip-public-98]]
