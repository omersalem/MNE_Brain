# Branch Connectivity Baseline

Last updated: 2026-06-06
Purpose: Document the current best-known ministry branch topology, routing model, and branch access gaps.

## Evidence Level

This document is based on:

- existing branch-related knowledge already present in the workspace
- central FortiGate and core-switch findings
- newly provided branch credentials
- live reachability checks performed from the current workstation
- live read-only branch FortiGate SSH validation on reachable sites
- live read-only branch switch SSH validation on reachable sites

Primary reference sources:

- `D:\projects\Ai enhancement\ai_knowledge_base_v2\13_AI_INDEX_BRANCH_CONNECTIVITY.md`
- `D:\projects\Ai enhancement\ai_knowledge_base_v2\05_ROUTING_AND_CONNECTIVITY.md`
- `D:\projects\Ai enhancement\ai_knowledge_base_v2\03_VLAN_SUBNET_INDEX.md`
- `D:\projects\Ai enhancement\ai_knowledge_base_v2\02_ADDRESS_REGISTRY.md`
- `D:\projects\cisco switch\knowledge_base\04_TRUNK_AND_UPLINKS.md`
- `D:\projects\cisco switch\knowledge_base\12_AI_INDEX_CRITICAL_LINKS.md`

## Branch Access Now Available

The project now has:

- branch switch credentials
- branch FortiGate credentials
- branch firewall management IPs
- branch switch management IPs
- live reachability evidence for most branches
- live authenticated FortiGate read-only validation for most reachable branches

Confirmed branch management IP pattern:

- FortiGate management uses `.1` in the branch subnet
- branch switch management uses `.3` in the branch subnet

| Branch | Firewall IP | Switch IP |
|---|---|---|
| Bethlehem | `10.60.18.1` | `10.60.18.3` |
| Hebron | `10.40.18.1` | `10.40.18.3` |
| Hebron Gold | `10.40.19.1` | `10.40.19.3` |
| Jenin | `10.201.18.1` | `10.201.18.3` |
| Jericho | `10.211.18.1` | `10.211.18.3` |
| Jerusalem | `10.70.18.1` | `10.70.18.3` |
| Qalqilya | `10.180.18.1` | `10.180.18.3` |
| Ramallah Gold | `10.110.19.1` | `10.110.19.3` |
| Salfeet | `10.235.18.1` | `10.235.18.3` |
| Tubas | `10.230.18.1` | `10.230.18.3` |
| Tulkarm | `10.165.18.1` | `10.165.18.3` |

## Central Branch Routing Model

Current best-known branch routing model from existing docs:

- all branch routes aggregate through the central FortiGate
- central branch gateway / next hop:
  - `172.23.13.201`
- branch aggregation network:
  - `172.23.13.200/30`
- main central interface for branches:
  - `port3`

Operational meaning:

- branches are centrally aggregated, not independently documented yet in this repo
- `port3` is currently the key branch interconnect on the central FortiGate side
- branch traffic is highly dependent on this single aggregation path

## Known Branch Subnets

From existing ministry knowledge already in the workspace, the following branch networks are known:

| Branch | Subnet |
|---|---|
| Bethlehem | `10.60.18.0/24` |
| Hebron | `10.40.18.0/24` |
| Jenin | `10.201.18.0/24` |
| Jericho | `10.211.18.0/24` |
| Jerusalem | `10.70.18.0/24` |
| Qalqilya | `10.180.18.0/24` |
| Ramallah branch / Gold Ramallah | `10.110.19.0/24` |
| Hebron Gold | `10.40.19.0/24` |

Additional branch names appear in the wider knowledge base but still need final normalization:

- Nablus
- Gold Nablus
- Salfit / Salfeet
- Tubas / Toubas
- Tulkarm / Toulkarem

## Live Reachability Summary

Branch firewall transport reachability from this workstation:

- reachable on SSH and HTTPS:
  - Bethlehem
  - Hebron
  - Hebron Gold
  - Jenin
  - Jerusalem
  - Qalqilya
  - Ramallah Gold
  - Salfeet
  - Tubas
  - Tulkarm
- unreachable on both SSH and HTTPS:
  - Jericho

Branch firewall authenticated read-only status:

- authenticated and validated:
  - Bethlehem
  - Hebron
  - Hebron Gold
  - Jenin
  - Jerusalem
  - Qalqilya
  - Salfeet
  - Tubas
  - Tulkarm
- reachable but authentication failed with the currently provided password:
  - Ramallah Gold
- unreachable:
  - Jericho

Branch switch transport reachability from this workstation:

- SSH and HTTPS reachable:
  - Bethlehem
  - Hebron
  - Jenin
  - Jerusalem
  - Qalqilya
  - Salfeet
  - Tubas
  - Tulkarm
- HTTPS reachable but SSH not confirmed:
  - Hebron Gold
  - Ramallah Gold
- unreachable on both SSH and HTTPS:
  - Jericho

## Live Branch FortiGate Findings

Validated branch firewall pattern:

- most reachable branches are `FortiGate-71G` on FortiOS `7.4.11 build2878`
- Jerusalem is `FortiGate-71G` on FortiOS `7.4.12 build2902`
- most sites have:
  - one central-facing `172.27.13.x` link
  - one public `213.6.x.x` WAN
  - one branch LAN on the documented `10.x.18.1` or `10.x.19.1` gateway
  - a default route pointing to the public WAN next hop

Validated site details:

| Branch | Hostname | Version | Key Interfaces / Notes |
|---|---|---|---|
| Bethlehem | `FW-MNE-Bethlahem` | `7.4.11` | `wan1 172.27.13.14/24`, `wan2 213.6.108.18/30`, `internal 10.60.18.1/24`, `WiFi 192.168.3.1/24` |
| Hebron | `FW-MNE-Hebron` | `7.4.11` | `wan1 172.27.13.62/30`, `wan2 213.6.112.10/30`, `internal 10.40.18.1/24`, `WiFi 192.168.1.1/24` |
| Hebron Gold | `FW-MNE-GoldH` | `7.4.11` | `wan1 213.6.107.94/30`, `fortilink 172.27.13.42/30`, `lan 10.40.19.1/24`, `port6 10.100.100.100/24`, `wqt.root 10.253.255.254/20`, `Gold-WiFi 192.168.5.1/24` |
| Jenin | `FW-MNE-Jenin` | `7.4.11` | `wan1 172.27.13.26/30`, `wan2 213.6.192.118/30`, `internal 10.201.18.1/24` |
| Jerusalem | `FW-MNE-Quds` | `7.4.12` | `wan1 172.27.13.22/30`, `wan2 213.6.108.22/30`, `lan 10.70.18.1/24`, `port6 10.10.10.1/24`, `fortilink 10.255.1.1/24`, `wqt.root 10.253.255.254/20`, `Quds-WiFi 192.168.6.1/24` |
| Qalqilya | `FW-MNE-Qalqilyah` | `7.4.11` | `wan1 172.27.13.46/30`, `wan2 213.6.192.170/30`, `internal 10.180.18.1/24`, `Qalq_MNE 192.168.4.1/24` |
| Salfeet | `FW-MNE-Salfeet` | `7.4.11` | `wan1 172.27.13.30/30`, `wan2 213.6.192.142/30`, `internal 10.235.18.1/24`, `Salf_WIFI 192.168.9.1/24` |
| Tubas | `FW-MNE-Tubas` | `7.4.11` | `wan1 172.27.13.18/30`, `wan2 213.6.192.150/30`, `internal 10.230.18.1/24`, `Tubas_WiFI 192.168.7.1/24` |
| Tulkarm | `MNE-Tulkarem` | `7.4.11` | `wan1 172.27.13.50/30`, `wan2 213.6.192.158/30`, `internal 10.165.18.1/24`, `fortilink 169.254.1.1/24` |

Operational note from live device output:

- Hebron
- Hebron Gold
- Jenin
- Jerusalem
- Qalqilya
- Salfeet
- Tubas

These firewalls reported a filesystem warning recommending `execute disk scan 1`. That should be treated as an operational health follow-up, not changed automatically in this read-only phase.

## Live Branch Switch Findings

Authenticated read-only SSH collection succeeded on these branch switches:

- Jerusalem:
  - prompt `switch6c70cc#`
  - software `4.1.3.36`
- Qalqilya:
  - prompt `QalqilyaSW#`
  - software `4.1.3.36`
- Salfeet:
  - prompt `switch6c8fba#`
  - software `4.1.3.36`
- Tubas:
  - prompt `TubasSW#`
  - software `4.1.3.36`

Switch access quirks observed:

- Bethlehem:
  - SSH transport reachable but host key algorithm negotiation failed
- Hebron:
  - SSH transport reachable but login negotiation returned an unusual authentication-type response
- Jenin:
  - SSH transport reachable but login negotiation returned an unusual authentication-type response
- Tulkarm:
  - SSH transport reachable but login negotiation did not complete cleanly
- Hebron Gold and Ramallah Gold:
  - HTTPS reachable, so browser or alternative SSH compatibility checks should be used next

This suggests multiple branch switches belong to the same family and software train, but some devices need compatibility handling beyond the default Paramiko settings.

## Branch Security and Policy Model

Current best-known central policy logic:

- branch subnets are grouped into `Branches-Group`
- `Branches-Group` is nested inside the broader `Users` zone or user-access model
- branch users inherit many of the same user-side access policies as campus users

Observed policy patterns from existing docs include branch access to:

- SharePoint
- Exchange-related services
- Apex / Trade applications
- IT admin resources
- VoIP
- internet access through central WAN

This suggests:

- the ministry is using a hub-and-spoke style central security model
- branch traffic is mainly enforced centrally rather than entirely at each branch

## Cross-Domain Relationship to Current Central Infrastructure

Branch traffic best-known path:

`Branch subnet -> branch gateway/device -> central FortiGate port3 -> central policy -> Fujitsu/core/FTD/server zones`

This ties branches directly to:

- central FortiGate
- core switching
- Cisco FTD segmentation
- server VLANs
- voice and application services

## Current Branch Knowledge Quality

What is already reasonably known:

- branch subnet list for several branches
- central branch aggregation next hop
- central FortiGate policy role
- branch inheritance into user-zone policies
- some branch-to-application traffic examples

What is still missing:

- branch site inventory with exact device names
- branch WAN handoff details
- per-branch local VLANs / local subnets
- branch internet breakout versus central breakout confirmation
- branch VPN / IPsec details per site

## Main Risks

1. Jericho branch is currently unreachable from this workstation on both the firewall and switch management IPs.
2. Ramallah Gold firewall is reachable but the currently provided password did not authenticate.
3. Several branch switches need SSH compatibility tuning or HTTPS-based collection to complete their validation.
4. Branch naming normalization is still inconsistent across sources.
5. We still do not know which branch services are enforced locally versus centrally for each site.

## Recommended Next Steps

1. troubleshoot Jericho branch reachability
2. correct or re-verify the Ramallah Gold firewall password
3. expand branch switch collection using HTTPS or broader SSH compatibility handling
4. map branch-to-central VPN or MPLS relationships
5. document per-branch local VLANs and local service segments
6. normalize branch names:
   - Salfit vs Salfeet
   - Toubas vs Tubas
   - Toulkarem vs Tulkarm
   - Jerusalem vs jeruslaem spelling variants
