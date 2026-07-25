# 12 — EHM (End Host Mode)
## Fujitsu PSWITCH 2048P (ET-7648BFRA-FOS) | FW 1.3.x

---

## OVERVIEW

EHM (End Host Mode) is a Fujitsu proprietary feature enabling the switch to operate
as an intelligent endpoint aggregator, primarily used in SPBM (Shortest Path Bridging MAC)
network topologies and data center environments with IEEE 802.1Aq.

---

## SHOW COMMANDS

```bash
show ehm
show ehm port
show ehm pin-group
show ehm pin-state
show spbm
show spbm interface
show isis
show isis neighbors
show isis database
```

---

## ENABLING EHM

```
(Config)# end-host-mode enable
show ehm
```

---

## PIN GROUP (Uplink Selection Group)

```
(Config)# ehm pin-group 1
(Config-ehm-pingroup)# uplink interface 0/49
(Config-ehm-pingroup)# uplink interface 0/50
(Config-ehm-pingroup)# exit

# Assign downlink ports to a pin group
(Interface 0/1)# ehm pin-group 1
(Interface 0/2)# ehm pin-group 1

show ehm pin-group 1
show ehm pin-state
```

---

## PINNING PROCESS

EHM automatically pins each server-facing (downlink) port to one uplink within its pin group.

| Pin State | Meaning |
|-----------|---------|
| `PINNED` | Port is actively pinned to an uplink |
| `BACKUP` | Secondary path available |
| `PINNING` | Pin negotiation in progress |
| `FAILED` | No valid uplink found |

```
show ehm pin-state
```

### Re-Pinning
Triggered automatically when uplink fails. Re-pin timer:
```
(Config-ehm-pingroup)# repin-timer 5          ← 5 seconds before re-pin
```

### Link Down Relay
When an uplink in the pin group goes down, EHM can bring down the corresponding downlinks:
```
(Config-ehm-pingroup)# link-down-relay enable
```

---

## SPBM (Shortest Path Bridging MAC — IEEE 802.1Aq)

SPBM uses IS-IS as the control plane to build loop-free Layer 2 paths.

```
(Config)# spbm enable
(Config)# router isis
(Config-router)# net 49.0001.0000.0001.0001.00
(Config-router)# is-type level-1

(Interface 0/49)# isis enable
(Interface 0/49)# isis spbm enable

show isis
show isis neighbors
show isis database
show spbm
```

---

## CONFIGURATION EXAMPLE (EHM with VPC)

```
# Enable EHM
(Config)# end-host-mode enable

# Create pin group with two uplinks
(Config)# ehm pin-group 1
(Config-ehm-pingroup)# uplink interface lag 10      ← VPC peer-link as uplink
(Config-ehm-pingroup)# repin-timer 3
(Config-ehm-pingroup)# link-down-relay enable
(Config-ehm-pingroup)# exit

# Assign server ports
(Config)# interface 0/1-0/12
(Interface 0/1-0/12)# ehm pin-group 1
(Interface 0/1-0/12)# exit

show ehm pin-state
```
