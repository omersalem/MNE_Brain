# 06 — LLDP / Port Mirroring / RSPAN
## Fujitsu PSWITCH 2048P (ET-7648BFRA-FOS) | FW 1.3.x

---

## LLDP (Link Layer Discovery Protocol)

### Show Commands
```bash
show lldp
show lldp neighbors
show lldp neighbors detail
show lldp interface 0/1
show lldp statistics
show lldp local-device
```

### Configuration
```
(Config)# lldp run                              ← enable LLDP globally
(Config)# no lldp run                           ← disable
(Config)# lldp holdtime 120                     ← TTL = 120s (default: 120)
(Config)# lldp timer 30                         ← transmit interval (default: 30s)
(Config)# lldp reinit 2                         ← reinit delay (default: 2s)

# Per-port LLDP
(Interface 0/1)# lldp transmit                  ← enable TX on port
(Interface 0/1)# lldp receive                   ← enable RX on port
(Interface 0/1)# no lldp transmit
(Interface 0/1)# no lldp receive

# TLV selection
(Interface 0/1)# lldp tlv-select system-name
(Interface 0/1)# lldp tlv-select port-desc
(Interface 0/1)# lldp tlv-select system-capabilities
(Interface 0/1)# lldp tlv-select management-address
```

> **NOTE:** When connected to Cisco CFX2000, LLDP may print:
> `ETS[lldpTask]: Incompatible configuration from neighbor detected on port 0/51`
> This is informational only — not a fault.

---

## PORT MIRRORING (SPAN)

### Local SPAN
```
(Config)# monitor session 1 source interface 0/5 both     ← tx+rx
(Config)# monitor session 1 source interface 0/5 tx       ← tx only
(Config)# monitor session 1 source interface 0/5 rx       ← rx only
(Config)# monitor session 1 destination interface 0/10
show monitor session 1
show monitor session all
no monitor session 1
```

### RSPAN (Remote SPAN — across switches)
```
# On source switch:
(Vlan)# vlan 200 remote-span
(Vlan)# exit
(Config)# monitor session 1 source interface 0/5 both
(Config)# monitor session 1 destination remote vlan 200

# On destination switch:
(Config)# monitor session 1 source remote vlan 200
(Config)# monitor session 1 destination interface 0/20
```

---

## FDB UPDATE (after STP topology change)

```
(Config)# mac-address-table notification change
show mac-addr-table notification
```
