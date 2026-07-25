# 01 — System & Management Commands
## Fujitsu PSWITCH 2048P (ET-7648BFRA-FOS) | FW 1.3.x

---

## SHOW COMMANDS

```bash
# Version and hardware info
show version
# Output includes: firmware version, build time, serial, MAC

# System summary
show system

# Running configuration
show running-config
show running-config interface 0/1

# Startup configuration
show startup-config

# All three config files
show startup-config
show backup-config

# System logging
show logging
show logging buffered
show logging traplogs

# Clock / NTP
show clock
show sntp

# CPU and memory
show process cpu
show process memory

# Users and sessions
show users
show sessions

# Tech-support (diagnostic dump)
show tech-support

# Inventory / hardware
show hardware

# Environment (fans, PSU, temperature)
show environment
show environment fans
show environment power
show environment temperature
```

---

## CONFIGURATION COMMANDS

### Hostname
```
(Config)# hostname MY-SWITCH
```

### Clock / SNTP
```
(Config)# clock timezone +3 0                   ← UTC+3
(Config)# sntp client mode unicast
(Config)# sntp server 192.168.1.1
(Config)# sntp server 192.168.1.1 version 4
show sntp
```

### Management IP (OOB Port)
```
(Config)# serviceport ip 10.0.0.2 255.255.255.0
(Config)# serviceport defaultgateway 10.0.0.1
(Config)# serviceport protocol none              ← static IP
(Config)# serviceport protocol dhcp             ← DHCP
show serviceport
```

### DNS
```
(Config)# ip domain-name example.com
(Config)# ip name-server 8.8.8.8
```

### SSH Configuration
```
(Config)# ip ssh server enable
(Config)# ip ssh protocol 2                      ← SSHv2 only
(Config)# crypto key generate rsa               ← Generate RSA key
show ip ssh
```

### Telnet Configuration
```
(Config)# ip telnet server enable
(Config)# ip telnet server disable
```

### Web GUI (REST API — requires FW 1.3.40+)
```
(Config)# ip http server enable
(Config)# ip https server enable
(Config)# ip https port 443
show ip http
```

### User Management
```
(Config)# username admin password admin123
(Config)# username oper privilege 1 password oper123
# Privilege levels: 1 = user, 15 = admin
show users accounts
```

### Banners
```
(Config)# banner motd # Authorized Access Only #
```

### Console Timeout
```
(Config)# line console
(Config-line)# exec-timeout 10 0     ← 10 minutes
(Config-line)# exit
```

### Save / Copy Configuration
```
# Save running to startup (persistent)
copy running-config startup-config

# Copy to USB
copy running-config usb://config.cfg

# Copy from USB
copy usb://config.cfg startup-config

# Copy to TFTP
copy running-config tftp://192.168.1.10/switch.cfg

# Copy from TFTP
copy tftp://192.168.1.10/switch.cfg running-config

# Restore backup config
copy backup-config startup-config

# Erase factory defaults
erase factory-defaults
reboot
```

### Reboot / Reload
```
(ET-7648BFRA-FOS)# reload
(ET-7648BFRA-FOS)# reboot
```

### Logging Configuration
```
(Config)# logging on
(Config)# logging buffered 512
(Config)# logging host 192.168.1.50         ← Syslog server
(Config)# logging facility local7
(Config)# logging severity informational
show logging
show logging buffered
clear logging buffered
```

### SYSLOG Severity Levels
| Level | Name | Description |
|-------|------|-------------|
| 0 | Emergency | System unusable |
| 1 | Alert | Immediate action needed |
| 2 | Critical | Critical conditions |
| 3 | Error | Error conditions |
| 4 | Warning | Warning conditions |
| 5 | Notice | Normal but significant |
| 6 | Informational | Informational messages |
| 7 | Debug | Debug messages |

---

## SCRIPTING

```
# List scripts
dir

# Run a script
script apply myconfig.scr

# Delete temp script
script delete temp-config.scr
```

> **NOTE (FW bug fixed in 1.2.21):** A temp file `temp-config.scr` may appear
> after `copy` commands. It can be removed with `script delete temp-config.scr`.
