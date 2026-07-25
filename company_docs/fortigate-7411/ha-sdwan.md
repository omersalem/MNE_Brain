# High Availability (HA) & SD-WAN — FortiOS 7.4.11

## HA — Active-Passive Cluster

### GUI: System > HA

```bash
# Primary unit configuration
config system ha
  set mode a-p                   # active-passive (or a-a for active-active)
  set group-id 1                 # must match on both units (0-255)
  set group-name "FW-Cluster-01"
  set password "HA-Secret@123"
  set hbdev "port5" 50 "port6" 40   # heartbeat interfaces (name priority)
  set session-sync-dev "port5"   # session sync interface
  set priority 200               # higher = primary (default: 128)
  set override enable            # return to primary after recovery
  set monitor "port1" "port3"    # monitored interfaces (failover if down)
  set ha-mgmt-status enable      # dedicated management interface
  config ha-mgmt-interfaces
    edit 1
      set interface "mgmt"
      set gateway 10.0.0.1
    next
  end
end

# Secondary unit — same config but lower priority
config system ha
  set mode a-p
  set group-id 1
  set group-name "FW-Cluster-01"
  set password "HA-Secret@123"
  set hbdev "port5" 50 "port6" 40
  set priority 100               # lower priority = secondary
  set override enable
  set monitor "port1" "port3"
end
```

## HA Diagnostics

```bash
# Cluster status
get sys ha status
exec ha manage 1 admin           # connect to secondary unit (index 0=primary)

# Cluster event history
diag sys ha history read

# Config sync check
diag sys ha checksum cluster     # compare checksums across cluster members
diag sys ha checksum recalculate # force recalculation

# Uptime and failover info
diag sys ha dump-by vcluster
diag sys ha reset-uptime         # reset uptime counter

# Manual failover
exec ha failover set 0           # force failover to secondary

# Debug HA sync
diag debug appl hasync -1
diag debug appl hatalk -1
diag debug enable
```

## Active-Active HA

```bash
config system ha
  set mode a-a
  set load-balance-all enable    # load balance all traffic
  # In A-A, FortiGate uses load balancing to distribute sessions
  # Primary handles new session assignment; all units process traffic
end
```

---

## SD-WAN

### GUI: Network > SD-WAN

### Step 1 — Enable SD-WAN and add members

```bash
config system sdwan
  set status enable
  config members
    edit 1
      set interface "port1"
      set gateway 203.0.113.254
      set cost 0
      set priority 1
      set comment "ISP1-Primary"
    next
    edit 2
      set interface "port2"
      set gateway 198.51.100.254
      set cost 10
      set priority 2
      set comment "ISP2-Backup"
    next
  end
end

# Update default route to use SD-WAN zone
config router static
  edit 1
    set dst 0.0.0.0 0.0.0.0
    set sdwan-zone "virtual-wan-link"   # sd-wan virtual zone
  next
end
```

### Step 2 — Health Checks (SLA Probes)

```bash
config system sdwan
  config health-check
    edit "Ping-ISP1"
      set server "8.8.8.8"
      set protocol ping
      set interval 500           # probe interval (ms)
      set failtime 5             # consecutive failures = link down
      set recoverytime 5
      set members 1              # apply to member 1
      config sla
        edit 1
          set latency-threshold 150   # ms
          set jitter-threshold 30     # ms
          set packetloss-threshold 1  # %
        next
      end
    next
    edit "HTTP-Check"
      set server "detectportal.firefox.com"
      set protocol http
      set http-get "/"
      set http-match "success"
      set interval 1000
      set members 1 2            # apply to both members
    next
  end
end
```

### Step 3 — SD-WAN Rules (Traffic Steering)

```bash
config system sdwan
  config service
    # Rule 1: Best quality (lowest latency) for VoIP
    edit 1
      set name "VoIP-Best-Quality"
      set mode lowest-quality
      set link-cost-factor latency jitter packet-loss
      set src "all"
      set dst "all"
      set protocol 17            # UDP
      set start-port 5060
      set end-port 5061
      set health-check "Ping-ISP1"
      set priority-members 1 2
    next
    # Rule 2: Preferred interface for cloud apps
    edit 2
      set name "MS365-Preferred"
      set mode manual
      set src "all"
      set internet-service enable
      set internet-service-name "Microsoft-Office365"
      set priority-members 1     # prefer ISP1
    next
    # Rule 3: Lowest cost (SLA-based) for general traffic
    edit 3
      set name "General-SLA"
      set mode sla
      set src "all"
      set dst "all"
      set health-check "HTTP-Check"
      config sla
        edit 1
          set health-check "HTTP-Check"
          set id 1
        next
      end
      set priority-members 1 2
    next
  end
end
```

## SD-WAN Diagnostics

```bash
diag sys sdwan member                          # member status
diag sys sdwan health-check status             # SLA probe results
diag sys sdwan health-check status filter "Ping-ISP1"
diag sys sdwan service <rule-id>               # rule state
diag sys sdwan intf-sla-log <intf-name>        # interface SLA history
diag sys sdwan sla-log <sla-name> <link-id>   # SLA log for specific link

# Link monitor test
diag test appl lnkmtd 0                        # statistics
diag test appl lnkmtd 1                        # dump link monitor data
diag debug appl link-mon -1                    # real-time debugger

# Speed test (GUI: Network > SD-WAN > Speed Test)
exec speed-test                                # CLI speed test
```

## SD-WAN with IPsec Overlay (Hub-and-Spoke)

```bash
# Create IPsec tunnels with hub (one per ISP link)
# then add tunnel interfaces as SD-WAN members
config system sdwan
  config members
    edit 3
      set interface "VPN-Hub-via-ISP1"
      set cost 0
    next
    edit 4
      set interface "VPN-Hub-via-ISP2"
      set cost 10
    next
  end
end
```
