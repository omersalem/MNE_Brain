# 02 — Interfaces & Ports
## Fujitsu PSWITCH 2048P (ET-7648BFRA-FOS) | FW 1.3.x

---

## PORT NUMBERING

| Range | Type | Description |
|-------|------|-------------|
| `0/1` – `0/48` | SFP+ 10GbE | Down-link data ports |
| `0/49` – `0/54` | QSFP+ 40GbE | Up-link/inter-switch ports |
| `serviceport` | RJ45 OOB | Out-of-band management |

Range syntax: `0/1-0/8` (ports 1 through 8)

---

## SHOW COMMANDS

```bash
show interfaces                            # All interfaces summary
show interfaces 0/1                        # Specific port detail
show interfaces 0/1-0/8                    # Range
show interfaces status                     # Link/speed/duplex table
show interfaces counters                   # Traffic counters
show interfaces counters errors            # Error counters only
show interfaces counters rate              # Rate statistics
show interfaces transceiver                # SFP/QSFP info (Tx/Rx power)
show interfaces transceiver 0/1
show interfaces switchport                 # Switchport info for all
show interfaces switchport 0/1
show port all                              # Port config summary
show port 0/1
```

---

## INTERFACE CONFIGURATION

### Enter Interface Config
```
(Config)# interface 0/1
(Config)# interface 0/1-0/8          ← range
(Config)# interface 0/49             ← uplink QSFP+
```

### Enable / Disable Port
```
(ET-7648BFRA-FOS)(Interface 0/1)# shutdown          ← disable port
(ET-7648BFRA-FOS)(Interface 0/1)# no shutdown       ← enable port
```

### Speed and Duplex
```
(Interface 0/1)# speed 10000        ← 10G (SFP+ forced)
(Interface 0/1)# duplex full
(Interface 0/1)# auto-negotiate     ← enable auto-negotiation
```

### Description
```
(Interface 0/1)# description "Uplink to Core Switch"
```

### Flow Control
```
(Interface 0/1)# flowcontrol send off
(Interface 0/1)# flowcontrol receive off
# Options: on | off | desired
```

### Jumbo Frames (MTU)
```
(Interface 0/1)# mtu 9216           ← max jumbo frame
# Default MTU: 1518
```

### EEE (Energy Efficient Ethernet)
```
(Interface 0/1)# eee                ← enable EEE
(Interface 0/1)# no eee             ← disable EEE
```

### Port Locator (LED blink)
```
(ET-7648BFRA-FOS)# port locator 0/1 on
(ET-7648BFRA-FOS)# port locator 0/1 off
```

### Switchport Mode
```
(Interface 0/1)# switchport mode access
(Interface 0/1)# switchport mode trunk
(Interface 0/1)# switchport mode general  ← flexible trunk/access
```

### Access VLAN Assignment
```
(Interface 0/1)# switchport mode access
(Interface 0/1)# switchport access vlan 100
```

### Trunk Configuration
```
(Interface 0/1)# switchport mode trunk
(Interface 0/1)# switchport trunk allowed vlan 10,20,30
(Interface 0/1)# switchport trunk allowed vlan add 40
(Interface 0/1)# switchport trunk allowed vlan remove 10
(Interface 0/1)# switchport trunk allowed vlan all
(Interface 0/1)# switchport trunk native vlan 1
```

---

## SFP/QSFP MODULES (1G SFP in 10GbE port)

To use a 1G SFP module in a 10GbE SFP+ port:
```
(Config)# interface 0/5
(Interface 0/5)# speed 1000
(Interface 0/5)# no auto-negotiate
```
Supported 1G SFP modules: `S26361-F3986-E1` (1000Base-T), `S26361-F3986-E2` (1000Base-SX)

---

## INTERFACE ERROR-DISABLE & AUTO-RECOVERY

```
(Config)# errdisable recovery cause all
(Config)# errdisable recovery interval 300
show errdisable recovery
show interfaces status err-disabled
```

---

## PORT MIRRORING (SPAN)

```
(Config)# monitor session 1 source interface 0/5 both
(Config)# monitor session 1 destination interface 0/10
show monitor session 1

# RSPAN (Remote SPAN — mirror across switches via VLAN)
(Config)# monitor session 1 source interface 0/5
(Config)# monitor session 1 destination remote vlan 200
```

---

## STORM CONTROL

```
(Interface 0/1)# storm-control broadcast level 20        ← 20% threshold
(Interface 0/1)# storm-control multicast level 20
(Interface 0/1)# storm-control unicast level 20
(Interface 0/1)# storm-control action shutdown           ← shutdown on storm
(Interface 0/1)# storm-control action trap               ← trap on storm
show storm-control
```

---

## PORT SECURITY

```
(Config)# interface 0/1
(Interface 0/1)# switchport port-security
(Interface 0/1)# switchport port-security maximum 5      ← max 5 MACs
(Interface 0/1)# switchport port-security violation shutdown
(Interface 0/1)# switchport port-security mac-address sticky
show port-security
show port-security interface 0/1
```

---

## UDLD (Unidirectional Link Detection)

```
(Config)# udld enable                  ← global
(Interface 0/1)# udld port             ← normal mode
(Interface 0/1)# udld port aggressive  ← aggressive mode
show udld
show udld interface 0/1
(ET-7648BFRA-FOS)# udld reset         ← reset err-disabled ports
```
