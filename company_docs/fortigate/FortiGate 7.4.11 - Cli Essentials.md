# CLI Essentials & System Management — FortiOS 7.4.11

## System Status & Info

```bash
get system status              # firmware version, serial, hostname, HA mode
get system performance status  # CPU, memory, sessions, uptime
get hardware status            # hardware model info
exec tac report                # generate full TAC support report
diag hardware deviceinfo nic   # hardware NIC list
```

## Administrator Accounts

### GUI: System > Administrators

```bash
# Create admin account
config system admin
  edit "newadmin"
    set password "SecurePass123!"
    set accprofile "super_admin"      # or custom profile
    set trusthost1 10.0.0.0 255.255.255.0  # restrict source IP
    set two-factor fortitoken         # optional 2FA
    set email-to "admin@company.com"
  next
end

# Admin profiles
config system accprofile
  edit "read-only-profile"
    set secfabgrp read
    set ftviewgrp read
    set authgrp read
    set sysgrp read
    set netgrp read
    set loggrp read
    set fwgrp read
    set vpngrp read
    set utmgrp read
    set wanoptgrp read
    set wifi read
  next
end

# List all admins
show system admin
```

## Backup & Restore

### GUI: Dashboard > Status > System Information > Configuration > Backup

```bash
# Backup via CLI (TFTP)
exec backup config tftp <filename.conf> <tftp-server-ip>

# Backup via SCP
exec backup config scp <filename.conf> <scp-server-ip> <user> <path>

# Restore from TFTP
exec restore config tftp <filename.conf> <tftp-server-ip>

# Reset to factory defaults (CAUTION!)
exec factoryreset
exec factoryreset2   # keeps management IP

# Check config errors after restore/upgrade
diag debug config-error-log read
```

## Firmware Management

### GUI: Dashboard > Status > Firmware > Update Firmware

```bash
# Check current version
get system status | grep Version

# Upgrade via TFTP
exec restore image tftp <firmware.out> <tftp-server-ip>

# Check upgrade path (use online tool)
# https://docs.fortinet.com/upgradetool/fortigate

# Show available firmware (FortiGuard)
diag fdsm image-list
diag fdsm imageupdate-matrix

# After upgrade — check for config errors
diag debug config-error-log read
```

## Hostname & DNS & NTP

```bash
config system global
  set hostname "FW-HQ-01"
  set timezone 04           # UTC+4 for Gulf/UAE; use '?' to list all
  set admin-sport 443
  set admin-ssh-port 22
  set admintimeout 30       # GUI/CLI session timeout (minutes)
end

config system dns
  set primary 8.8.8.8
  set secondary 8.8.4.4
  set domain "company.local"
end

config system ntp
  set type custom
  set ntpsync enable
  config ntpserver
    edit 1
      set server "pool.ntp.org"
    next
  end
end
```

## Feature Visibility

### GUI: System > Feature Visibility

```bash
config system settings
  set gui-vpn enable          # show VPN menu
  set gui-wireless-controller enable
  set gui-switch-controller enable
  set gui-load-balance enable
  set gui-explicit-proxy enable
  set gui-ztna enable
end
```

## VDOM (Virtual Domains)

```bash
# Enable VDOMs (requires reboot awareness)
config system global
  set vdom-admin enable
end

# Create VDOM
config vdom
  edit "branch-vdom"
  next
end

# Switch to a VDOM context
config vdom
  edit branch-vdom
end

# Assign interface to VDOM
config system interface
  edit port3
    set vdom "branch-vdom"
  next
end

# Inter-VDOM routing link
config system vdom-link
  edit "vlink0"
    set vcluster-id 0
  next
end
```

## Certificate Management

```bash
# Import certificate (GUI: System > Certificates > Import)
# Local certificate for HTTPS/SSL inspection
config vpn certificate local
  edit "my-cert"
    set certificate "-----BEGIN CERTIFICATE-----..."
    set private-key "-----BEGIN RSA PRIVATE KEY-----..."
  next
end

# CA certificate for SSL inspection
config vpn certificate ca
  edit "my-ca"
    set ca "-----BEGIN CERTIFICATE-----..."
  next
end

# Set GUI certificate
config system global
  set admin-server-cert "my-cert"
end

# NOTE (7.4.11): RSA keys must be minimum 2048 bits
# GUI cannot be accessed if server cert uses RSA 1024 bit key
```

## SNMP Configuration

```bash
config system snmp sysinfo
  set status enable
  set description "FortiGate HQ"
  set contact-info "admin@company.com"
  set location "Server Room 1"
end

config system snmp community
  edit 1
    set name "public"
    config hosts
      edit 1
        set ip 10.0.0.100 255.255.255.255  # NMS server
      next
    end
  next
end
```

## Syslog & FortiAnalyzer Logging

```bash
# FortiAnalyzer
config log fortianalyzer setting
  set status enable
  set server "192.168.1.200"
  set reliable enable           # TCP reliable logging
  set enc-algorithm high        # AES-256 encryption
end

# Syslog server
config log syslogd setting
  set status enable
  set server "192.168.1.201"
  set port 514
  set facility local7
  set format rfc5424
end

# Log filter — what to log
config log fortianalyzer filter
  set traffic enable
  set attack enable
  set virus enable
  set webfilter enable
  set severity information
end
```
