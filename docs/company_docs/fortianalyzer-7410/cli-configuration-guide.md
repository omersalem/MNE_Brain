# FortiAnalyzer 7.4.10 — Command Line Interface (CLI) Guide

This guide provides the complete CLI commands, syntax, and operational procedures for **FortiAnalyzer 7.4.10 (build 2778)** running on `172.23.71.206`.

---

## 1. Connecting to the CLI

Connect via SSH from any allowed management terminal:
```bash
ssh admin@172.23.71.206
# Password: refer to local .env (MNE_FORTIANALYZER_PASSWORD)
```
When authenticated, the prompt appears as:
```
FAZVM64 #
```

---

## 2. System Status & Diagnostic Commands

### 2.1 Appliance Identity & License Status
```bash
get system status
```
*Displays firmware build (`v7.4.10-build2778`), serial number (`FAZVMSTM24000372`), license validity, system time, and uptime.*

### 2.2 System Performance & Resource Consumption
```bash
get system performance
```
*Outputs real-time CPU utilization per core, memory consumption, swap space, and hard disk I/O stats (TPS, KB/s write/read).*

### 2.3 Filesystem & Disk Partition Utilization
```bash
diagnose system print df
```
*Shows raw Linux disk partitions, mount points, used blocks, and available percentages on `/var` and the Ext4 data store.*

---

## 3. Network, Routing & DNS Configuration

### 3.1 Interface IP & Allowed Management Protocols
```bash
config system interface
    edit "port1"
        set ip 172.23.71.206 255.255.255.0
        set allowaccess ping https ssh http
        set status enable
    next
end
```
> **Security Recommendation:** To disable unencrypted HTTP and enforce HTTPS only:
> ```bash
> config system interface
>     edit "port1"
>         set allowaccess ping https ssh
>     next
> end
> ```

### 3.2 Static Routing & Gateway Configuration
```bash
config system route
    edit 1
        set device "port1"
        set gateway 172.23.71.4
    next
end
```

To display current routing table:
```bash
get system route
show system route
```

### 3.3 DNS Servers Configuration
```bash
config system dns
    set primary 172.23.71.27
    set secondary 172.23.71.28
end
```

---

## 4. System Global & Security Hardening

### 4.1 System Timezone & NTP
```bash
config system global
    set timezone 36
    set daylightsavetime enable
end

config system ntp
    config ntpserver
        edit 1
            set server "172.23.71.27"
        next
        edit 2
            set server "ntp1.fortinet.net"
        next
    end
    set status enable
end
```

### 4.2 Web Admin Session Timeout & Port Binding
```bash
config system admin setting
    set idle_timeout 15
    set https-port 443
    set http-port 80
end
```

### 4.3 SSH Strong Cryptography & Cipher Suites
To enforce modern SSH security ciphers and disable legacy weak MACs/algorithms:
```bash
config system global
    set ssh-strong-crypto enable
end
```

---

## 5. Administrator Accounts & Profiles

### 5.1 Changing Administrator Password
```bash
config system admin user
    edit "admin"
        set password <new-complex-password>
    next
end
```

### 5.2 Creating a Restricted Read-Only Administrator
```bash
# 1. Create the read-only profile
config system admin profile
    edit "ReadOnly_SOC"
        set devicemanager read
        set fortiview read
        set logview read
        set report read
        set system-setting read
    next
end

# 2. Create the user assigned to this profile with trusted hosts
config system admin user
    edit "soc_auditor"
        set profileid "ReadOnly_SOC"
        set password <secure-password>
        set trusthost1 172.23.50.0 255.255.255.0
        set trusthost2 172.23.71.0 255.255.255.0
    next
end
```

---

## 6. Device Management via CLI

### 6.1 Listing All Managed and Unregistered Devices
```bash
diagnose dvm device list
```
*Displays all 14 managed firewalls, registration status, IP addresses, serial numbers, firmware versions, and ADOM associations.*

### 6.2 Authorizing / Promoting an Unregistered Device
When a new FortiGate sends logs to FortiAnalyzer, it appears with `cond: unregistered`. To promote it to managed status via CLI:
```bash
execute device promote <device-name-or-serial>
```

### 6.3 Checking Connectivity to a Managed Device
```bash
execute ping <device_ip>
diagnose dvm device get <device_name>
```

---

## 7. Storage, ADOMs & Database Maintenance

### 7.1 Inspecting Storage Usage by Device and ADOM
```bash
diagnose log device
```
*Outputs raw log volume, SQL database usage, retention periods, and percentage of quota consumed per ADOM and per individual device.*

### 7.2 Rebuilding SQL Database Index (Troubleshooting)
If reports fail or logs appear missing in Log View despite arriving via Syslog/OFTP:
```bash
# Rebuild SQL database index for root ADOM:
execute sql-local rebuild-adom root
```

### 7.3 Checking Log Daemon Status & Throughput
```bash
diagnose log logd-status
```
*Displays current log insertion rate, logs received per second, and database lag.*

---

## 8. Backup, Restore & Maintenance Commands

### 8.1 Backing Up Configuration to Remote SFTP/FTP Server
```bash
execute backup config sftp <filepath.dat> <sftp-server-ip> <username> <password>
```

### 8.2 Safe System Reboot & Shutdown
```bash
# Graceful reboot:
execute reboot

# Graceful shutdown (power off):
execute shutdown
```
