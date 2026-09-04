# 04 — LAG / LACP / VPC (Multi-Chassis LAG)
## Fujitsu PSWITCH 2048P (ET-7648BFRA-FOS) | FW 1.3.x

---

## LIMITS

| Item | Limit |
|------|-------|
| Max LAGs | 64 |
| Max members per LAG | 8 |
| LAG numbering | `lag 1` – `lag 64` |
| LACP modes | Active, Passive |
| VPC peer switches | 2 |

---

## SHOW COMMANDS

```bash
show port-channel brief
show port-channel 1
show lacp summary
show lacp neighbor
show lacp counters
show lacp interface 0/17
show vpc
show vpc brief
show vpc role
show vpc peer-keepalive
```

---

## STATIC LAG

```
# Goal: Ports 0/1 and 0/2 → Static LAG 1
(Config)# interface 0/1-0/2
(Interface 0/1-0/2)# channel-group 1 mode on
(Interface 0/1-0/2)# exit

(Config)# interface lag 1
(Interface lag 1)# no shutdown
(Interface lag 1)# description "Static LAG to Server"
(Interface lag 1)# exit

show port-channel 1
```

---

## DYNAMIC LAG (LACP)

```
# Goal: Ports 0/17 and 0/18 → LACP LAG 2
(Config)# interface 0/17-0/18
(Interface 0/17-0/18)# channel-group 2 mode active    ← active or passive
(Interface 0/17-0/18)# exit

(Config)# interface lag 2
(Interface lag 2)# no shutdown
(Interface lag 2)# description "LACP to Core"
(Interface lag 2)# exit

show lacp summary
```

### LACP Timers
```
(Interface 0/17)# lacp timeout short     ← fast: 1s hello, 3s dead
(Interface 0/17)# lacp timeout long      ← slow: 30s hello, 90s dead (default)
```

### LACP Port Priority
```
(Interface 0/17)# lacp port-priority 100    ← lower = preferred (default 32768)
```

### LAG Hashing Algorithm
```
(Config)# port-channel load-balance src-dst-mac
(Config)# port-channel load-balance src-dst-ip
(Config)# port-channel load-balance src-dst-mac-ip  ← default
show port-channel load-balance
```

---

## VPC (Virtual Port Channel) — Multi-Chassis LAG

VPC allows two PSWITCH switches to appear as a single LAG endpoint.

### VPC Topology Roles
- **Primary**: Manages VPC operations
- **Secondary**: Backup switch

### VPC Configuration — Step by Step

#### Step 1: VPC Keepalive Link (direct L3 link between the two switches)
```
# On BOTH switches — configure L3 keepalive interface
(Config)# interface 0/48
(Interface 0/48)# no switchport                      ← make it L3 routed
(Interface 0/48)# ip address 169.254.1.1 255.255.255.0   ← Switch A
# Switch B: 169.254.1.2
(Interface 0/48)# no shutdown
```

#### Step 2: VPC Domain
```
(Config)# vpc domain 1
(Config-vpc-domain)# peer-keepalive destination 169.254.1.2 source 169.254.1.1
(Config-vpc-domain)# exit
```

#### Step 3: Peer-Link (VPC inter-switch link — must be trunk)
```
# Ports 0/49-0/50 as peer-link LAG 10
(Config)# interface 0/49-0/50
(Interface 0/49-0/50)# channel-group 10 mode active
(Interface 0/49-0/50)# exit

(Config)# interface lag 10
(Interface lag 10)# switchport mode trunk
(Interface lag 10)# switchport trunk allowed vlan all
(Interface lag 10)# vpc peer-link
(Interface lag 10)# exit
```

#### Step 4: VPC Member Ports (downlink LAG to servers)
```
(Config)# interface 0/1-0/2
(Interface 0/1-0/2)# channel-group 5 mode active
(Interface 0/1-0/2)# exit

(Config)# interface lag 5
(Interface lag 5)# switchport mode trunk
(Interface lag 5)# vpc 5                            ← same VPC ID on both switches
(Interface lag 5)# exit
```

### VPC Status & Verification
```
show vpc
show vpc brief
show vpc role
show vpc peer-keepalive
show vpc consistency-parameters
show vpc statistics
```

### VPC Known Issues / Limitations (FW 1.3.x)
- Peer-link **down** → ~3 seconds traffic interruption
- Peer-link **up** → ~15 seconds recovery time
- When ALL VPC member ports go down on the Primary device → some packet loss on peer-link until one port recovers
- VPC Enhance Mode available for faster convergence
- 40G twinax cable **NOT** supported for peer-link to CFX2000
