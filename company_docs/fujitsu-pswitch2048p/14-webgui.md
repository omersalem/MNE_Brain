# 14 — Web GUI Navigation
## Fujitsu PSWITCH 2048P (ET-7648BFRA-FOS) | FW 1.3.40+

---

## ACCESS

```
URL:      http://<management-IP>   OR   https://<management-IP>
Default:  Username: admin  |  password = secret_ref("MNE_PLATFORM_READONLY_CREDENTIAL")MNE_DEVICE_READONLY_PASSWORD")
Browser:  Chrome, Firefox, Edge (modern versions)
```

> Web GUI (REST API-based) was introduced in **FW 1.3.40**.
> Available in FW 1.3.68.

---

## GUI LAYOUT

```
┌─────────────────────────────────────────────────────┐
│  HEADER: Device name | Status | Logout              │
├───────────────┬─────────────────────────────────────┤
│               │                                     │
│  LEFT NAV     │   MAIN CONTENT AREA                 │
│  (Menu Tree)  │                                     │
│               │                                     │
└───────────────┴─────────────────────────────────────┘
```

---

## NAVIGATION MENU STRUCTURE

### System
```
System
  ├── Dashboard              ← Port status overview, health
  ├── System Information     ← Version, serial, MAC
  ├── Management Interface   ← OOB IP settings
  ├── Clock                  ← NTP / manual time
  ├── Logging                ← Syslog, severity filter
  ├── User Accounts          ← Add/edit local users
  └── Session Management     ← Active sessions
```

### Switching (Layer 2)
```
Switching
  ├── VLANs
  │     ├── VLAN Configuration    ← Create/delete VLANs
  │     ├── Port VLAN Membership  ← Assign ports to VLANs
  │     └── VLAN Statistics
  ├── MAC Address Table
  │     ├── Dynamic Entries
  │     ├── Static Entries
  │     └── Aging Time
  ├── Spanning Tree
  │     ├── STP Global Settings
  │     ├── STP Per-Port Settings
  │     └── STP Statistics
  ├── Link Aggregation
  │     ├── LAG Configuration
  │     ├── LACP Settings
  │     └── LAG Statistics
  ├── Port Mirroring
  └── Storm Control
```

### Interfaces
```
Interfaces
  ├── Interface Configuration    ← Speed, duplex, description, shutdown
  ├── Interface Status           ← Link state, counters
  ├── Interface Counters         ← Detailed TX/RX stats
  ├── SFP/QSFP Status            ← Transceiver info, Tx/Rx power
  └── Port Security
```

### Routing (Layer 3)
```
Routing
  ├── IP Interfaces              ← SVIs and routed ports
  ├── ARP Table
  ├── Routing Table              ← Static + dynamic routes
  ├── Static Routes
  ├── OSPF
  │     ├── OSPF Configuration
  │     ├── OSPF Neighbors
  │     └── OSPF Database
  ├── BGP
  ├── RIP
  └── VRRP
```

### Security & AAA
```
Security
  ├── User Management
  ├── RADIUS Servers
  ├── TACACS+ Servers
  ├── LDAP
  ├── 802.1X
  │     ├── Global 802.1X Settings
  │     └── Port 802.1X Settings
  ├── ACL
  │     ├── IP ACL
  │     └── MAC ACL
  ├── Dynamic ARP Inspection
  ├── DHCP Snooping
  └── IP Source Guard
```

### QoS
```
QoS
  ├── Class Map
  ├── Policy Map
  ├── QoS Interface Settings     ← Trust, queue weights
  ├── DSCP Mapping
  └── DCB
        ├── PFC Settings
        ├── ETS Settings
        └── DCBX Settings
```

### Management Protocols
```
Management
  ├── SNMP
  │     ├── Community Strings    ← v1/v2c
  │     ├── SNMPv3 Users
  │     ├── Trap Receivers
  │     └── SNMP Statistics
  ├── LLDP
  │     ├── LLDP Global Settings
  │     ├── LLDP Port Settings
  │     └── LLDP Neighbors Table
  └── sFlow
        ├── sFlow Global
        ├── Collectors
        └── Interface Settings
```

### Maintenance
```
Maintenance
  ├── Firmware Upgrade           ← Upload via TFTP or HTTP
  ├── Backup / Restore Config    ← Download/upload config file
  ├── Save Config                ← Copy running → startup
  ├── Factory Reset
  ├── Reboot
  └── Tech-Support Download      ← Download diagnostic bundle
```

---

## KEY GUI WORKFLOWS

### Save Configuration via GUI
```
Maintenance → Save Config → Click "Save"
```

### Firmware Upgrade via GUI
```
Maintenance → Firmware Upgrade
  → Select method: TFTP or File Upload
  → Enter TFTP server IP and filename
  → Click "Upgrade"
  → Reboot when prompted
```

### Create VLAN via GUI
```
Switching → VLANs → VLAN Configuration
  → Click "Add"
  → Enter VLAN ID and Name
  → Click "Apply"
```

### Assign Port to VLAN via GUI
```
Switching → VLANs → Port VLAN Membership
  → Select VLAN
  → Check ports as Tagged or Untagged
  → Click "Apply"
```

### View Port Status via GUI
```
System → Dashboard         (visual port panel — green/grey = up/down)
Interfaces → Interface Status
```

### Configure LAG via GUI
```
Switching → Link Aggregation → LAG Configuration
  → Select LAG ID
  → Add member ports
  → Set mode: Static or LACP
  → Click "Apply"
```
