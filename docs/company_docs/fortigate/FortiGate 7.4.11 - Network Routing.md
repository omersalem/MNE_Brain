# Network & Routing — FortiOS 7.4.11

## Interface Configuration

### GUI: Network > Interfaces

```bash
# Physical interface
config system interface
  edit "port1"
    set vdom "root"
    set mode static
    set ip 203.0.113.1 255.255.255.0
    set allowaccess ping https ssh
    set role wan
    set description "WAN-ISP1"
    set mtu-override enable
    set mtu 1500
    set speed auto              # or: 100full, 1000full, 10000full
    set status up
  next
end

# LAN interface
config system interface
  edit "port3"
    set vdom "root"
    set mode static
    set ip 192.168.10.1 255.255.255.0
    set allowaccess ping https ssh fgfm
    set role lan
    set device-identification enable
  next
end

# DHCP client on interface
config system interface
  edit "port1"
    set mode dhcp
    set defaultgw enable
    set dns-server-override enable
  next
end

# Interface roles
# WAN  — upstream internet link (shows BW settings in GUI)
# LAN  — internal network (shows DHCP server in GUI)
# DMZ  — demilitarized zone
# Undefined — general purpose
```

## VLAN Interfaces

```bash
config system interface
  edit "VLAN10-Users"
    set vdom "root"
    set interface "port3"        # parent (trunk) interface
    set vlanid 10
    set mode static
    set ip 10.10.10.1 255.255.255.0
    set allowaccess ping
    set role lan
  next
  edit "VLAN20-Servers"
    set interface "port3"
    set vlanid 20
    set ip 10.20.20.1 255.255.255.0
    set role lan
  next
end
```

## Hardware Switch (Internal Switch)

```bash
# Create hardware switch (for models that support it)
config system virtual-switch
  edit "internal"
    set physical-switch "sw0"
    config port
      edit "port2"
      next
      edit "port3"
      next
      edit "port4"
      next
    end
  next
end
```

## Software Switch / Zone

```bash
# Zone — group interfaces for simplified policy
config system zone
  edit "LAN-Zone"
    set interface "port3" "VLAN10-Users" "VLAN20-Servers"
    set intrazone allow          # or: deny
  next
end
```

## DHCP Server

```bash
config system dhcp server
  edit 1
    set dns-service default      # use FGT's DNS
    set default-gateway 192.168.10.1
    set netmask 255.255.255.0
    set interface "port3"
    config ip-range
      edit 1
        set start-ip 192.168.10.100
        set end-ip 192.168.10.200
      next
    end
    set dns-server1 8.8.8.8
    set dns-server2 8.8.4.4
    set lease-time 86400         # 24 hours
    # Static reservation
    config reserved-address
      edit 1
        set mac 00:11:22:33:44:55
        set ip 192.168.10.50
        set description "Printer"
      next
    end
  next
end
```

## Static Routes

### GUI: Network > Static Routes

```bash
# Default route
config router static
  edit 1
    set dst 0.0.0.0 0.0.0.0
    set gateway 203.0.113.254
    set device "port1"
    set distance 10              # lower = preferred
    set priority 1               # lower = preferred (when distance equal)
    set comment "Default via ISP1"
  next
  # Second WAN (higher distance = backup)
  edit 2
    set dst 0.0.0.0 0.0.0.0
    set gateway 198.51.100.254
    set device "port2"
    set distance 20
    set comment "Default via ISP2 (backup)"
  next
end

# Blackhole route (null route)
config router static
  edit 10
    set dst 10.0.0.0 255.255.0.0
    set blackhole enable
  next
end
```

## Policy-Based Routes (PBR)

```bash
config router policy
  edit 1
    set input-device "port3"
    set src 192.168.10.0 255.255.255.0
    set dst 0.0.0.0 0.0.0.0
    set gateway 198.51.100.254
    set output-device "port2"
    set comments "Route specific VLAN via ISP2"
  next
end
```

## Dynamic Routing — OSPF

```bash
config router ospf
  set router-id 10.0.0.1
  config area
    edit 0.0.0.0
      set authentication none    # or: md5
    next
  end
  config ospf-interface
    edit "LAN"
      set interface "port3"
      set area 0.0.0.0
      set network-type broadcast
      set cost 10
      set hello-interval 10
      set dead-interval 40
    next
  end
  config network
    edit 1
      set prefix 192.168.10.0 255.255.255.0
      set area 0.0.0.0
    next
  end
  set redistribute "connected" status enable
  set redistribute "static" status enable
end
```

## Dynamic Routing — BGP

```bash
config router bgp
  set as 65001
  set router-id 10.0.0.1
  config neighbor
    edit "203.0.113.254"
      set remote-as 65000        # ISP AS number
      set interface "port1"
      set description "ISP1 BGP peer"
      set keep-alive-timer 30
      set holdtime-timer 90
      set soft-reconfiguration enable
    next
  end
  # Advertise your prefix
  config network
    edit 1
      set prefix 203.0.113.0 255.255.255.0
    next
  end
end

# Useful BGP diagnostics
# get router info bgp summary
# get router info bgp neighbors 203.0.113.254 advertised-routes
# get router info bgp neighbors 203.0.113.254 routes
# exec router clear bgp all
```

## Routing Diagnostics

```bash
get router info routing-table all          # full routing table
get router info routing-table details x.x.x.x  # routing decision for specific IP
get router info routing-table database     # includes inactive routes
get router info kernel                     # kernel FIB (hardware forwarding table)
diag firewall proute list                  # policy-based routes
get router info protocols                  # active dynamic routing protocols
exec router restart                        # restart all routing daemons
diag ip address list                       # all IPs assigned to interfaces
diag netlink interface list                # interfaces with MTU
get hardware nic port1                     # NIC-level interface info
diag ip arp list                           # ARP table
exec clear system arp table               # flush ARP cache
```

## Strict RPF / Anti-Spoofing

```bash
config system settings
  set strict-src-check enable   # enable strict RPF (default: loose)
end
```
