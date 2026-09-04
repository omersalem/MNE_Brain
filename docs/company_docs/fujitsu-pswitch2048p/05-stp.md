# 05 — STP / RSTP / MSTP / PVRSTP
## Fujitsu PSWITCH 2048P (ET-7648BFRA-FOS) | FW 1.3.x

---

## SHOW COMMANDS

```bash
show spanning-tree
show spanning-tree brief
show spanning-tree active
show spanning-tree detail
show spanning-tree interface 0/1
show spanning-tree mst
show spanning-tree mst 0
show spanning-tree mst interface 0/1
show spanning-tree vlan 100              ← PVRSTP/PVSTP
```

---

## STP MODE SELECTION

```
(Config)# spanning-tree mode stp         ← Classic STP (802.1D)
(Config)# spanning-tree mode rstp        ← Rapid STP (802.1w) — default
(Config)# spanning-tree mode mstp        ← Multiple STP (802.1s)
(Config)# spanning-tree mode pvrstp      ← Per-VLAN Rapid STP
(Config)# spanning-tree mode pvstp       ← Per-VLAN STP
```

---

## GLOBAL STP SETTINGS

```
(Config)# spanning-tree                         ← enable STP globally
(Config)# no spanning-tree                      ← disable STP globally

# Priority (lower = more likely Root Bridge)
(Config)# spanning-tree priority 4096           ← multiples of 4096 (default 32768)

# Hello / Forward / Max-age timers
(Config)# spanning-tree hello-time 2
(Config)# spanning-tree forward-time 15
(Config)# spanning-tree max-age 20
```

---

## RSTP (Rapid STP)

```
(Config)# spanning-tree mode rstp
(Config)# spanning-tree priority 4096

# Per-port settings
(Interface 0/1)# spanning-tree portfast              ← Edge port (fast convergence)
(Interface 0/1)# spanning-tree portfast bpduguard    ← BPDU Guard on edge port
(Interface 0/1)# spanning-tree bpdufilter enable     ← BPDU Filter
(Interface 0/1)# spanning-tree bpduflood enable      ← BPDU Flood
(Interface 0/1)# spanning-tree guard root            ← Root Guard
(Interface 0/1)# spanning-tree guard loop            ← Loop Guard
(Interface 0/1)# spanning-tree cost 4                ← Port cost
(Interface 0/1)# spanning-tree port-priority 64      ← Port priority (default 128)

# Fast-Uplink (UplinkFast equivalent)
(Interface 0/1)# spanning-tree stp-pathcost-method long
```

---

## MSTP (Multiple STP)

```
(Config)# spanning-tree mode mstp
(Config)# spanning-tree mst configuration
(Config-mst)# name MY_REGION
(Config-mst)# revision 1
(Config-mst)# instance 1 vlan 10,20,30
(Config-mst)# instance 2 vlan 40,50
(Config-mst)# exit

# Set MST instance root bridge
(Config)# spanning-tree mst 1 priority 4096
(Config)# spanning-tree mst 2 priority 8192

# Per-port MST cost
(Interface 0/1)# spanning-tree mst 1 cost 20000
(Interface 0/1)# spanning-tree mst 1 port-priority 64
```

---

## PVRSTP / PVSTP (Per-VLAN STP)

```
(Config)# spanning-tree mode pvrstp

# Set root for specific VLAN
(Config)# spanning-tree vlan 100 priority 4096
(Config)# spanning-tree vlan 200 priority 8192

# Per-port per-VLAN cost
(Interface 0/1)# spanning-tree vlan 100 cost 4
(Interface 0/1)# spanning-tree vlan 100 port-priority 64
```

---

## LOOP PROTECTION

```
(Config)# loop-protection
(Interface 0/1)# loop-protection enable
show loop-protection
```

---

## LINK DEPENDENCY (Link-Down Relay)

```
(Config)# link-dependency group 1
(Config-ldep)# action link-down
(Config-ldep)# source interface 0/49         ← uplink (monitored)
(Config-ldep)# destination interface 0/1     ← downlink (affected)
(Config-ldep)# exit
show link-dependency
```

---

## UPSTREAM THRESHOLD

```
(Config)# interface 0/1
(Interface 0/1)# upstream-threshold 80      ← alert when 80% capacity
```
