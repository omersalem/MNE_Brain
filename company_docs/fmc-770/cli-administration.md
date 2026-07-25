# FMC 7.7.0 — CLI & System Administration

Covers: FMC appliance CLI, FTD device CLI (admin/diagnostic subset), expert/Linux shell,
sftunnel troubleshooting, backups, users, recovery-config mode.

## Table of Contents
1. FMC CLI reference
2. Expert mode (Linux shell) — use carefully
3. sftunnel (FMC↔FTD management channel)
4. Backups & restore
5. User & role administration
6. Recovery-config mode (FTD, new in 7.7.0)
7. GUI equivalents for system administration

---

## 1. FMC CLI reference

The FMC CLI is a restricted shell (not full Linux). Logging in via SSH or console drops you
straight into it as the `admin` user (or another configured CLI user).

```bash
# Identity / status
show version                    # FMC software version, build, VDB, LSP/SRU
show network                    # mgmt interfaces, routes, DNS, search domains
show network-static-routes
show hostname
show ntp                        # sync state vs configured NTP servers
show disk-manager               # per-category disk usage (events, backups, updates...)
show process tree
show process status <pid>
show cpu
show memory
show users                      # logged-in CLI/GUI sessions
show audit-log

# Network configuration
configure network ipv4 manual <ip> <netmask> <gateway>
configure network ipv4 dhcp
configure network ipv6 manual <ip>/<prefix-length> <gateway>
configure network dns servers <dns1> [<dns2> ...]
configure network dns searchdomains <domain1> [<domain2> ...]
configure network hostname <hostname>
configure network mtu <value>

# Note (deprecated in 10.0.0, still valid on 7.7.0):
configure network ipv4 dhcp-server-enable    # enable DHCP server on mgmt iface (legacy)
configure network ipv4 dhcp-server-disable
show network-dhcp-server

# Time
configure ntp <server1> [<server2>]
configure timezone

# Password / users (CLI-level shell accounts, separate from GUI internal users)
configure password
configure user add <username> <privilege: config|basic>
configure user delete <username>
configure user access <username> <config|basic>     # change privilege level
show user

# sftunnel / manager relationship (see section 3 for details)
configure manager add <FMC-ip-or-DONTRESOLVE> <reg-key> [<nat-id>]   # run on FTD, not FMC
show managers                                                          # run on FTD

# Reboot / shutdown
reboot
shutdown

# Backups (kick off from CLI; full config from GUI is more common)
backup
restore
```

### Reading FMC vs FTD versions from expert mode

To check the exact build numbers underlying a CLI `show version`, drop to expert mode:

```bash
expert
sudo cat /etc/sf/ims.conf | grep -i version
sudo build.sh   # build number / patch level, varies by appliance
```

---

## 2. Expert mode (Linux shell) — use carefully

```bash
expert              # from FMC or FTD CLI, drops to a restricted bash shell
sudo su -            # full root, only if genuinely needed (TAC-style troubleshooting)
exit                 # leave expert mode back to the CLI
exit                 # leave the CLI session entirely
```

Treat expert mode as a diagnostic/TAC tool, not a routine configuration path — changes made
here are **not tracked by FMC's deployment/config-history system** and can be silently
overwritten or cause drift. Typical legitimate uses:
- Inspecting log files under `/var/log/`, `/var/opt/CSCOpx/`, `/ngfw/var/log/` (paths vary by
  appliance role).
- Checking disk usage with `df -h`, `du -sh <dir>` when the GUI "Clear disk space" utility
  (new in 7.7.0, under the Disk Usage health widget) isn't enough detail.
- Validating certificate files, package integrity, or process status under TAC guidance.

Never edit FMC/FTD configuration files directly in expert mode to "fix" something the GUI
won't let you do — this is unsupported and can break upgrades.

---

## 3. sftunnel (FMC ↔ FTD management channel)

FMC manages FTD over a persistent, mutually-authenticated TLS tunnel called **sftunnel**
(TCP/8305 by default, FTD-initiated unless using a NAT-ID scenario). When a device shows
"Unknown" status or won't deploy, this is usually where to look.

```bash
# On the FTD device CLI:
show managers                      # confirms which FMC it's registered to, registration status
sftunnel-status                    # detailed tunnel status (may need expert mode: pmtool or process check)
show running-config sftunnel       # (varies by version) confirms NAT-ID / manager config

# Re-pointing or re-registering a device to its manager:
configure manager delete
configure manager add <FMC-ip-or-DONTRESOLVE> <registration-key> [<nat-id>]
```

On the **FMC side**, check device health from the GUI: **Devices > Device Management**, the
device's status icon, and (7.7.0+) **Device > Health > Out of Band Status** for any
recovery-config drift that's blocking reconnection.

If registration keeps failing after FMC HA failover or a device rebuild, 7.7.0 added a GUI
fix path — no CLI workaround needed anymore: from the FMC, **Devices > Device Management >
device > Disable Manager**, then **Add Manager** again, instead of clearing stale manager
data at the device CLI as in older versions.

---

## 4. Backups & restore

Mostly GUI-driven; use the CLI `backup`/`restore` commands only for scripted/manual restore
scenarios or when the GUI is unreachable.

**GUI path:** System/Administration > Tools > Backup/Restore
- FMC backup: configuration-only, or configuration + events (large).
- Device (FTD) backup: triggered from FMC, stored on FMC or a remote server.
- 7.7.0: the Message Center shows **detailed backup status** for FMC and devices, and you
  can now **cancel in-progress device backups** from there — useful if a backup is hanging
  and blocking other operations.
- 7.7.0: a **Clear disk space** button was added directly to the Disk Usage health widget
  (System/Administration > Health > Monitor) to safely purge old backups, content updates,
  and troubleshoot files when disk space alerts fire.

```bash
# CLI (FMC)
backup                       # interactive prompt for backup profile / destination
restore <backup-filename>    # restore from a previously generated backup file
```

Always back up before: major version upgrades, FMC HA configuration changes, bulk policy
edits, or before using `expert`/`sudo` to touch anything.

---

## 5. User & role administration

Two separate user concepts:
- **CLI shell users** (`configure user add/delete/access`) — basic vs config privilege,
  controls what they can do at the restricted CLI.
- **GUI internal users** (web interface accounts with RBAC roles like Administrator,
  Security Analyst, Access Admin, etc.) — managed entirely in the GUI, not the CLI.

**GUI path for web users:** System/Administration > Users > Add User (or edit existing).
Each user can now (7.7.0) have an **email address** field for product/release notifications.
External authentication (LDAP/AD/SAML/RADIUS) is configured under
Integration > Other Integrations > Realms, or System > Users > External Authentication.

7.7.0 added: **restrict SAML SSO logins to a subdomain** in multidomain deployments
(configurable only at the global domain level) — useful if Omar's ministry environment ever
moves to a multidomain FMC with SSO.

---

## 6. Recovery-config mode (FTD, new in 7.7.0)

Purpose: make **emergency, limited** configuration changes directly on an FTD device when it
has lost its management connection to FMC (e.g., a bad data-interface manager-access change
locked it out).

```bash
system support diagnostic-cli
configure recovery-config
# Inside recovery-config mode you can issue a restricted set of commands, including:
#   - interface settings: duplex, speed, negotiate-auto, fec
#   - NAT and related object/object-group commands
#   - shutdown (not supported on cluster control link or failover link)
```

After connectivity is restored, FMC does **not** auto-adopt these changes. You must:
1. Go to **Devices > Device Management > device > Health > Out of Band Status**.
2. Review the configuration differences FMC detected.
3. Acknowledge the drift.
4. Manually replicate the same changes in the FMC policy/object configuration.
5. Deploy — until you do, the device stays flagged as out-of-band/out-of-date.

This mode is not supported on the Firepower 4100/9300 chassis, ISA 3000, virtual FTD, or
Secure Firewall 3100/4200 in multi-instance mode.

---

## 7. GUI equivalents for system administration

| Task | GUI path |
|---|---|
| Network/DNS/NTP/hostname settings | System/Administration > Configuration > Management Interfaces / Network / Time Synchronization |
| Licensing | System/Administration > Licenses (Smart Licensing) |
| Health alert policy | System/Administration > Health > Policy |
| Health monitor / disk usage / clear disk space | System/Administration > Health > Monitor |
| Audit log | System/Administration > Audit |
| Change management / approval workflow | System/Administration > Change Management |
| Theme (Light/Dark/Legacy) | click username (top right) > select theme |
| HA setup for FMC itself | System/Administration > High Availability |
