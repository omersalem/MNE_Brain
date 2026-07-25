# 10 — QoS & DCB (PFC / ETS / ECN / DCBX / sFlow / QCN)
## Fujitsu PSWITCH 2048P (ET-7648BFRA-FOS) | FW 1.3.x

---

## SHOW COMMANDS

```bash
show qos
show qos interface 0/1
show qos map
show class-map
show policy-map
show policy-map interface 0/1
show dcb
show dcb pfc
show dcb ets
show dcbx interface 0/1
show priority-flow-control
show ecn
show sflow
show sflow agent
show sflow collectors
show sflow polling-interval
```

---

## QoS OVERVIEW

```
Queues per port: 8 (CoS 0–7)
Default scheduling: WRR (Weighted Round Robin)
Trust modes: CoS (L2), DSCP (L3), IP Precedence
```

---

## QoS TRUST

```
# Trust CoS (802.1p) — L2 switching
(Interface 0/1)# qos trust cos

# Trust DSCP — L3 routing
(Interface 0/1)# qos trust dscp

# Trust IP Precedence
(Interface 0/1)# qos trust ip-precedence

# No trust (mark to default CoS 0)
(Interface 0/1)# no qos trust
```

---

## DSCP → CoS MAPPING

```
(Config)# qos dscp-map 46 6            ← DSCP 46 (EF) → CoS 6
(Config)# qos dscp-map 34 4            ← DSCP 34 (AF41) → CoS 4
show qos map dscp-cos
```

---

## POLICY-MAP / CLASS-MAP (MQC Style)

```
(Config)# class-map match-all VOICE
(Config-classmap)# match dscp ef
(Config-classmap)# exit

(Config)# policy-map QOS-POLICY
(Config-pmap)# class VOICE
(Config-pmap-c)# set cos 6
(Config-pmap-c)# police 10000000 bps 64000 byte conform transmit exceed drop
(Config-pmap-c)# exit
(Config-pmap)# exit

(Interface 0/1)# service-policy input QOS-POLICY
show policy-map interface 0/1
```

---

## SCHEDULING (Queue Weighting)

```
(Config)# qos scheduler wrr             ← Weighted Round Robin (default)
(Config)# qos scheduler strict          ← Strict Priority

# WRR weights per CoS queue (0–7)
(Config)# qos wrr-queue bandwidth 5 10 15 20 1 1 1 1   ← 8 values
```

---

## ECN (Explicit Congestion Notification)

```
(Config)# ecn enable
(Interface 0/1)# ecn enable
show ecn
```

---

## DATA CENTER BRIDGING (DCB)

DCB suite: PFC + ETS + DCBX — required for FCoE / iSCSI lossless transport.

### PFC (Priority Flow Control — per-priority pause)
```
(Config)# priority-flow-control enable

(Interface 0/49)# priority-flow-control mode on
# Enable PFC on CoS 3 (iSCSI) and CoS 4 (FCoE)
(Interface 0/49)# priority-flow-control priority 3 enable
(Interface 0/49)# priority-flow-control priority 4 enable

show priority-flow-control
show dcb pfc interface 0/49
```

> **PFC Note:** Enabling PFC via `priority-flow-control` command causes a
> brief link down-up on device ports. This is expected behavior.

### ETS (Enhanced Transmission Selection)
```
(Config)# dcb ets enable

(Config)# dcb ets tc-bandwidth 0 20 1 10 1 1 1 1   ← % per TC (must sum to 100)
(Config)# dcb ets tc-tsa 0 ETS 1 strict 2 ETS       ← ETS or Strict per TC
(Config)# dcb ets tc-priority-map 0 0 1 1 2 2 3 3   ← CoS → Traffic Class
```

### DCBX (Data Center Bridging Exchange — auto-negotiate DCB via LLDP)
```
(Config)# dcbx enable
(Interface 0/49)# dcbx port-role auto-up              ← auto upstream role
(Interface 0/49)# dcbx port-role auto-down            ← auto downstream
(Interface 0/49)# dcbx port-role configuration-source ← manual config source

show dcbx interface 0/49
```

### FIP Snooping (FCoE Initialization Protocol)
```
(Config)# fip-snooping enable
(Config)# fip-snooping vlan 200
(Interface 0/49)# fip-snooping port-mode fcf-facing    ← uplink to FCF
show fip-snooping
```

### QCN (Quantized Congestion Notification — backward congestion)
```
(Config)# qcn enable
(Interface 0/1)# qcn enable
show qcn
```

---

## sFlow (Traffic Sampling)

```
(Config)# sflow enable
(Config)# sflow agent-address 192.168.1.10
(Config)# sflow collector 10.0.0.100 6343
(Config)# sflow polling-interval 20               ← counter polling (seconds)
(Config)# sflow sample-rate 512                   ← 1 in 512 packets sampled

# Per interface
(Interface 0/1)# sflow enable
(Interface 0/1)# sflow sample-rate 256

show sflow
show sflow collectors
show sflow polling-interval
show sflow interface 0/1
```
