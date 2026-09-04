# Main Device Link Port Discovery

Last updated: 2026-06-07
Purpose: Capture read-only SSH findings for the main topology diagram device links, with local ports, IPs, and remaining unknowns.

## Evidence Used

Read-only SSH commands were run against:

- FortiGate `FG-MNE` at `172.23.70.4`
- F5 BIG-IP WAF at `172.23.70.89`
- Fujitsu `MNE-CoreSw1` at `172.23.70.70`
- Fujitsu `MNE-CoreSw2` at `172.23.70.71`
- Cisco `CoreSwitch1` at `172.23.70.254`
- Cisco FTD `FTD-01` at `172.23.70.78`
- vCenter GUI / vSphere Client physical-adapter views for ESXi hosts `172.23.69.30-33`
- FMC GUI interface views for FTD EtherChannel membership

No write commands were used.

## Confirmed Main Link Labels For Diagram

| Link | Side A | Side B | Status |
|---|---|---|---|
| FortiGate to Fujitsu fabric | FortiGate aggregate `LAN`, members `x1` and `x2`, no IP on aggregate | Fujitsu SW1 `0/31` and SW2 `0/31`, trunk, description `To-FG-X1-Trunk`, `10G Full`, up | confirmed as trunk/fabric path |
| FortiGate WAF internal VLAN | FortiGate `WAF_IN`, IP `172.23.9.4/24`, VLAN `9`, parent `LAN` | F5 `Internal`, IP `172.23.9.50/24`, VLAN `9`, interface `1.1`, up `1000T-FD` | confirmed logical VLAN path |
| FortiGate WAF external/VIP VLAN | FortiGate `WAF_EX`, IP `172.23.10.4/24`, VLAN `10`, parent `LAN` | F5 `External`, IP `172.23.10.50/24`, VLAN `10`, interface `1.2`, up `1000T-FD` | confirmed logical VLAN path |
| FortiGate to FTD outside/transit | FortiGate `x3`, IP `172.23.200.1/24`, alias `FG-CISCO-FW`, up `10G` | FTD `Port-channel1`, IP `172.23.200.2/24`, nameif `Outside`, members `Ethernet1/9` + `Ethernet1/10` | confirmed routed transit and FTD members |
| FTD inside/datacenter zones | FTD `Port-channel2`, no parent IP, nameif `Inside-DC`, members `Ethernet1/11` + `Ethernet1/12` | FTD subinterfaces `.30`, `.55`, `.69`, `.71`, `.72`, `.73`, `.74`, `.75`, `.78`, `.79`, `.80`, `.81`, `.88` | confirmed logical zone trunk and FTD members |
| Fujitsu to FTD management | Fujitsu SW1 `0/34`, VLAN `70`, description `To_FTD_Mgmt`, up `10G` | FTD management network `172.23.70.78`, management0 up `10G`; FTD CLI also shows `Management1/1` management-only | confirmed management path; exact FTD front-panel label should be treated carefully |
| Fujitsu to FTD VLAN 200 transit | Fujitsu SW1 `0/39` up, `0/40` down; Fujitsu SW2 `0/39` up, `0/40` up; VLAN `200` | FTD `Port-channel1` / FortiGate `x3` transit IPs `172.23.200.2` and `172.23.200.1` | confirmed VLAN role, partial member issue on SW1 `0/40` |
| Fujitsu to VMware ESXi hosts | ESXi `172.23.69.30-33`, active `vmnic3`, `vmnic4`, `vmnic5`, each `10G` | Fujitsu SW1 ports `0/19`, `0/20`, `0/21`, `0/22`; Fujitsu SW2 ports `0/19`, `0/20`, `0/21`, `0/22`, `0/23`, `0/24`, `0/25`, `0/26` | confirmed by vCenter MACs and Fujitsu MAC table |
| Fujitsu datacenter trunk | Fujitsu SW1 `0/46` up `10G`, SW2 `0/46` up `10G`, trunk | broader datacenter / infrastructure trunk, with FTD zone MACs learned through this path | confirmed fabric-side ports; not the primary ESXi vmnic mapping from current evidence |
| Fujitsu backbone/fabric pair | Fujitsu SW1 `0/53` up `40G`, `3/52` up; SW2 `0/53` up `40G`, `3/52` up | paired fabric/backbone relationship | confirmed fabric-side ports |
| Cisco core to older core/fabric neighbor | Cisco `TwentyFiveGigE2/0/6`, trunk, CDP neighbor `MNE-CORE-SW.met.gov.ps`, remote port `TenGigabitEthernet1/1/2`, neighbor IP `172.23.9.254` | Remote device `MNE-CORE-SW.met.gov.ps` | confirmed by CDP |
| Cisco core port-channel | Cisco `Po44`, trunk, LACP; member `Twe2/0/10` bundled, member `Twe1/0/10` down | remote side not confirmed in this pass | confirmed local state; redundancy degraded |
| FortiGate to branches | FortiGate `port3`, IP `172.23.13.202/30`, alias `Branches`, up; next hop documented as `172.23.13.201` | branch FW `.1` and branch SW `.3` per branch subnet | confirmed central interface and branch IP model |
| FortiGate WAN | FortiGate `port2`, IP `213.6.17.30/30`, alias `WAN2`, up | ISP next hop `213.6.17.29` | confirmed interface/IP |
| FortiGate WAN1 | FortiGate `port1`, IP `172.23.1.54/30`, alias `WAN1`, up | peer not identified in this pass | confirmed interface/IP only |

## Device-Specific Findings

### FortiGate

Use these labels in the simplified topology:

- `FG-MNE`
- management: `172.23.70.4`
- `port1`: `172.23.1.54/30`, alias `WAN1`, up
- `port2`: `213.6.17.30/30`, alias `WAN2`, up
- `port3`: `172.23.13.202/30`, alias `Branches`, up
- `LAN`: aggregate, members `x1` and `x2`
- `x1`: aggregate member, up `10G`
- `x2`: aggregate member, up `10G`
- `x3`: `172.23.200.1/24`, alias `FG-CISCO-FW`, up `10G`
- `WAF_IN`: `172.23.9.4/24`, VLAN `9`, parent `LAN`
- `WAF_EX`: `172.23.10.4/24`, VLAN `10`, parent `LAN`
- `port4`: no IP, down

### F5 BIG-IP

Use these labels in the simplified topology:

- management: `172.23.70.89`
- `Internal`: `172.23.9.50/24`, VLAN `9`, interface `1.1`, up `1000T-FD`
- `External`: `172.23.10.50/24`, VLAN `10`, interface `1.2`, up `1000T-FD`
- `mgmt`: up `100TX-FD`

F5 LLDP did not return useful neighbor data.

### Fujitsu Fabric

Use these labels in the simplified topology:

- `MNE-CoreSw1`: `172.23.70.70`
- `MNE-CoreSw2`: `172.23.70.71`
- both SW1/SW2 `0/31`: trunk, `To-FG-X1-Trunk`, up `10G`
- SW1 `0/34`: VLAN `70`, `To_FTD_Mgmt`, up `10G`
- SW2 `0/34`: VLAN `70`, `To FTD-01 Management1/1`, down
- SW1 `0/39`: VLAN `200`, up `10G`
- SW1 `0/40`: VLAN `200`, down
- SW2 `0/39`: VLAN `200`, up `10G`
- SW2 `0/40`: VLAN `200`, up `10G`
- both SW1/SW2 `0/46`: datacenter trunk, up `10G`
- both SW1/SW2 `0/53`: backbone/fabric pair, up `40G`
- ESXi direct MAC mappings:
  - SW1 `0/19`: ESXi `172.23.69.32` `vmnic5`
  - SW1 `0/20`: ESXi `172.23.69.31` `vmnic5`
  - SW1 `0/21`: ESXi `172.23.69.33` `vmnic5`
  - SW1 `0/22`: ESXi `172.23.69.30` `vmnic5`
  - SW2 `0/19`: ESXi `172.23.69.30` `vmnic3`
  - SW2 `0/20`: ESXi `172.23.69.31` `vmnic3`
  - SW2 `0/21`: ESXi `172.23.69.33` `vmnic3`
  - SW2 `0/22`: ESXi `172.23.69.32` `vmnic3`
  - SW2 `0/23`: ESXi `172.23.69.33` `vmnic4`
  - SW2 `0/24`: ESXi `172.23.69.30` `vmnic4`
  - SW2 `0/25`: ESXi `172.23.69.32` `vmnic4`
  - SW2 `0/26`: ESXi `172.23.69.31` `vmnic4`

Fujitsu MAC table evidence:

- F5 MAC `14:A9:D0:63:C8:8C` appears in VLAN `9` and VLAN `10`
- On SW1 it is learned through `3/52`
- On SW2 it is learned through `3/44`
- This proves the F5 VLANs are visible in the fabric, but it does not prove a direct front-panel cable endpoint by LLDP.

### Cisco Core

Use these labels in the simplified topology:

- `CoreSwitch1`: `172.23.70.254`
- SVI `Vlan9`: `172.23.9.254`
- SVI `Vlan70`: `172.23.70.254`
- SVI `Vlan1011`: `10.11.12.4`
- `TwentyFiveGigE2/0/6`: CDP neighbor `MNE-CORE-SW.met.gov.ps`, remote `TenGigabitEthernet1/1/2`, neighbor IP `172.23.9.254`
- `Po44`: trunk, LACP, up
- `Twe2/0/10`: bundled in `Po44`
- `Twe1/0/10`: down in `Po44`

### Cisco FTD

Use these labels in the simplified topology:

- management address from FXOS/management plane: `172.23.70.78`
- `management0`: `172.23.70.78/24`, gateway `172.23.70.4`, up `10G`
- diagnostic CLI also shows `Management1/1`, management-only; do not overlabel this as the same thing as a data-plane routed interface
- `Port-channel1`: `172.23.200.2/24`, nameif `Outside`, up
- `Port-channel1` EtherChannel ID `1`, physical members:
  - `Ethernet1/9`
  - `Ethernet1/10`
- `Port-channel2`: no parent IP, nameif `Inside-DC`, up
- `Port-channel2` EtherChannel ID `2`, physical members:
  - `Ethernet1/11`
  - `Ethernet1/12`
- `Port-channel2.30`: `172.23.30.4/24`, `ARBS-30`
- `Port-channel2.55`: `172.23.55.4/24`, `Server-55`
- `Port-channel2.69`: `172.23.69.4/24`, `Server-Mgmt-69`
- `Port-channel2.71`: `172.23.71.4/24`, `Servers-71`
- `Port-channel2.72`: `172.23.72.4/24`, `Trade-72`
- `Port-channel2.73`: `172.23.73.4/24`, `Sophos-73`
- `Port-channel2.74`: `172.23.74.4/24`, `ERCompany-74`
- `Port-channel2.75`: `172.23.75.4/24`, `Database-75`
- `Port-channel2.78`: `172.23.78.4/24`, `Application-78`
- `Port-channel2.79`: `172.23.79.4/24`, `Web-79`
- `Port-channel2.80`: `172.23.80.4/24`, `sec-80`
- `Port-channel2.81`: `172.23.81.4/24`, `hr-clock-81`
- `Port-channel2.88`: `172.23.88.4/24`, `UXP-88`

FTD physical member interfaces for `Port-channel1` and `Port-channel2` were confirmed from the FMC GUI interface editor.

### VMware ESXi To Fujitsu Mapping

Active ESXi physical adapters from vCenter:

| ESXi Host | vmnic | MAC | Speed | Fujitsu Port |
|---|---|---|---|---|
| `172.23.69.30` | `vmnic3` | `4c:52:62:50:82:8e` | `10G` | SW2 `0/19` |
| `172.23.69.30` | `vmnic4` | `4c:52:62:50:82:8f` | `10G` | SW2 `0/24` |
| `172.23.69.30` | `vmnic5` | `4c:52:62:50:82:90` | `10G` | SW1 `0/22` |
| `172.23.69.31` | `vmnic3` | `4c:52:62:50:bd:4a` | `10G` | SW2 `0/20` |
| `172.23.69.31` | `vmnic4` | `4c:52:62:50:bd:4b` | `10G` | SW2 `0/26` |
| `172.23.69.31` | `vmnic5` | `4c:52:62:50:bd:4c` | `10G` | SW1 `0/20` |
| `172.23.69.32` | `vmnic3` | `4c:52:62:50:7b:42` | `10G` | SW2 `0/22` |
| `172.23.69.32` | `vmnic4` | `4c:52:62:50:7b:43` | `10G` | SW2 `0/25` |
| `172.23.69.32` | `vmnic5` | `4c:52:62:50:7b:44` | `10G` | SW1 `0/19` |
| `172.23.69.33` | `vmnic3` | `4c:52:62:50:82:62` | `10G` | SW2 `0/21` |
| `172.23.69.33` | `vmnic4` | `4c:52:62:50:82:63` | `10G` | SW2 `0/23` |
| `172.23.69.33` | `vmnic5` | `4c:52:62:50:82:64` | `10G` | SW1 `0/21` |

Inactive / do not draw as active ESXi uplinks:

- `vmnic0`, `vmnic1`, and `vmnic2` are down / no active network in the vCenter views for the shown ESXi hosts.

## Still Missing Or Not Fully Proven

- exact front-panel switch port directly connected to F5 `1.1`
- exact front-panel switch port directly connected to F5 `1.2`
- exact remote side of Cisco `Po44`
- exact branch firewall-to-branch-switch physical ports at each branch

## Simplified Diagram Prompt Snippet

Use this compact link data in the image prompt:

```text
Draw only main devices and confirmed links.

FortiGate FG-MNE 172.23.70.4:
port1 172.23.1.54/30 WAN1 up
port2 213.6.17.30/30 WAN2 up
port3 172.23.13.202/30 Branches up
LAN aggregate x1+x2 up 10G
x3 172.23.200.1/24 FG-CISCO-FW up 10G
WAF_IN 172.23.9.4/24 VLAN9 on LAN
WAF_EX 172.23.10.4/24 VLAN10 on LAN

Fujitsu SW1 172.23.70.70 and SW2 172.23.70.71:
0/31 trunk To-FG-X1-Trunk up 10G to FortiGate LAN aggregate
0/34 VLAN70 FTD management: SW1 up, SW2 down
0/39 VLAN200 FG-FTD transit up on SW1 and SW2
0/40 VLAN200 FG-FTD transit down on SW1, up on SW2
0/46 datacenter trunk up 10G
0/53 backbone/fabric pair up 40G

F5 BIG-IP 172.23.70.89:
1.1 Internal VLAN9 172.23.9.50/24 up 1000T-FD
1.2 External VLAN10 172.23.10.50/24 up 1000T-FD
mgmt up 100TX-FD

Cisco FTD 172.23.70.78:
management0 172.23.70.78/24 gateway 172.23.70.4 up 10G
Port-channel1 Outside 172.23.200.2/24 up, EtherChannel ID 1, members Ethernet1/9 + Ethernet1/10, connected to FortiGate x3 172.23.200.1/24 through VLAN200/Fujitsu fabric
Port-channel2 Inside-DC up, EtherChannel ID 2, members Ethernet1/11 + Ethernet1/12, subinterfaces 30/55/69/71/72/73/74/75/78/79/80/81/88

VMware ESXi to Fujitsu:
172.23.69.30 vmnic3 -> SW2 0/19, vmnic4 -> SW2 0/24, vmnic5 -> SW1 0/22
172.23.69.31 vmnic3 -> SW2 0/20, vmnic4 -> SW2 0/26, vmnic5 -> SW1 0/20
172.23.69.32 vmnic3 -> SW2 0/22, vmnic4 -> SW2 0/25, vmnic5 -> SW1 0/19
172.23.69.33 vmnic3 -> SW2 0/21, vmnic4 -> SW2 0/23, vmnic5 -> SW1 0/21

Cisco CoreSwitch1 172.23.70.254:
TwentyFiveGigE2/0/6 trunk to MNE-CORE-SW.met.gov.ps remote TenGigabitEthernet1/1/2, neighbor IP 172.23.9.254
Po44 trunk up; Twe2/0/10 bundled; Twe1/0/10 down
SVIs: Vlan9 172.23.9.254, Vlan70 172.23.70.254, Vlan1011 10.11.12.4

Branches:
FortiGate port3 172.23.13.202/30 to branch aggregation next hop 172.23.13.201.
Show branches as grouped spokes with FW .1 and SW .3 management IPs.

Mark unknowns:
F5 switch-side ports pending
Branch local physical ports pending
```
