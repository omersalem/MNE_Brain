# FMC 7.7.0 — Device Management, High Availability, Clustering

Covers: registering FTDs to FMC, FMC high availability, FTD high availability, clustering,
multi-instance mode, device templates, recovery-config / out-of-band detection.

## Table of Contents
1. Registering a device to FMC
2. FMC high availability (manager redundancy)
3. FTD high availability (active/standby pair)
4. Clustering (active/active scale-out)
5. Multi-instance mode
6. Device templates (zero-touch provisioning)
7. Out-of-band change detection (7.7.0)

---

## 1. Registering a device to FMC

**On the FTD device (CLI, during/after initial setup):**

```bash
configure manager add <FMC-ip-or-hostname-or-DONTRESOLVE> <registration-key> [<nat-id>]
# Example, FMC reachable directly:
configure manager add 10.10.10.5 Cisco123Key
# Example, FMC behind NAT (use DONTRESOLVE + matching nat-id on both ends):
configure manager add DONTRESOLVE Cisco123Key mySharedNatId
```

**On FMC (GUI):** Devices > Device Management > **Add > Device**.
- 7.7.0 removed the old separate "Add > Device (Wizard)" entry — the wizard *is* now the only
  path (legacy registration-key-only screens are deprecated as of 10.0.0, but on 7.7.0 you
  may still see both; prefer the wizard).
- The wizard supports both: device with registration key (manual `configure manager add` was
  already run on the FTD), and (since 7.6.1) device with registration key **plus basic
  initial configuration** pushed from FMC in the same flow.
- Fill in: device IP/hostname, registration key (must match what was configured on the
  device), and the access control policy to assign on registration.
- **Unregister** (renamed from "Delete" in 7.6.0) removes the device from FMC management
  without erasing its running configuration — traffic keeps flowing using the last-deployed
  config until you re-register or change it locally.

**Serial-number / zero-touch registration** (no IP needed up front): Devices > Device
Management > Add > Device (Wizard), choose serial-number registration. Requires Security
Cloud Control and (for registering multiple devices via Device Templates) FTD 7.4.1+ on the
device. Supported platforms: Firepower 1000/2100, Secure Firewall 1200/3100 family.

---

## 2. FMC high availability (manager redundancy)

Two FMCs (same model/license) form an active/standby pair; only the active one accepts
configuration changes and pushes deploys — the standby mirrors via synchronized config and
event data.

**GUI path:** System/Administration > High Availability (some FMCs may show this under
Integration > Other Integrations > High Availability depending on theme/version).
- Designate Primary/Secondary, peer management IPs, and a synchronization schedule.
- 7.7.0 improvements: easier visibility of **when peers last synced**, side-by-side
  **comparison of SRU/LSP and VDB versions** between peers, and a GUI fix (instead of CLI) for
  the classic "device registration fails on standby due to stale manager data" issue — use
  **Disable Manager** then **Add Manager** from the FMC GUI rather than touching the FTD CLI.
- Upgrading an HA pair (7.6.0+ workflow, still current in 7.7.0): you no longer manually copy
  the package to both peers, manually run readiness checks on both, or manually pause/resume
  sync — most of this is automated. You still must log into the second peer to kick off its
  own upgrade.

```bash
# CLI visibility only (HA itself is configured/managed via GUI):
show version          # confirm build match before/after HA setup
```

---

## 3. FTD high availability (active/standby pair)

Two identical FTD devices share a **failover link** (HA state sync) and (for stateful
failover) a **stateful link**, plus your data interfaces in active/standby roles.

**GUI path:** Devices > Device Management > **Add > High Availability**. Choose primary and
secondary peer, then configure the failover link and (optionally) stateful link interfaces.

**7.7.0 new:** Threat Defense HA now supports **redundant manager-access data interfaces** —
useful if your FTD pair manages access from FMC over a data interface rather than the
dedicated management interface, and you want resiliency on that path too.

**Also from 7.4.3 (still applies on 7.7.0):** failover convergence is faster — MAC-address
update broadcasts on failover now run asynchronously in the data plane rather than blocking
control-plane failover tasks.

```bash
# FTD CLI diagnostics:
show failover
show failover state
show failover history
show failover config-sync error      # detect config mismatches between HA peers (7.4.1+)
show failover config-sync stats
```

If replacing a failed HA unit from backup, FTD HA **automatically resumes** after the restore
completes and the device reboots (since 7.6.0) — you no longer need to manually re-enable HA,
but you should still confirm `show failover` reports normal state before deploying.

---

## 4. Clustering (active/active scale-out)

Supported on Firepower 4100/9300 and Secure Firewall 3100/4200 (up to 16 nodes as of 7.6.0).
One control node, multiple data nodes, all sharing a cluster control link (CCL).

**GUI path:** Devices > Device Management > **Add > Cluster** (or, on the chassis manager for
4100/9300 hardware, configure at the chassis level first).

```bash
# FTD CLI diagnostics:
show cluster info
show cluster info trace
show cluster history
show cluster vpn-sessiondb              # distributed site-to-site VPN (10.0.0+, Secure FW 4200)
cluster redistribute vpn-sessiondb
ping <ccl-peer-ip>                      # basic CCL reachability check
```

**MTU checks on node join:** the cluster pings the control node with a packet matching the
CCL MTU when a node joins; if that fails, the system now (10.0.0) automatically halves the
MTU and retries, generating a notification so you can fix the real MTU on your switches.
(7.6.0 added the same idea from the data-node side using 2x MTU.)

**Individual interface mode** (alternative to spanned EtherChannel, available since 7.6.0 on
Secure Firewall 3100/4200): each node gets its own routed IP, with a floating "main cluster
IP" that follows the control node — useful when your upstream switch can't do the load
balancing spanned EtherChannel needs.

---

## 5. Multi-instance mode

Lets one physical chassis (Secure Firewall 3100, 4200, or Firepower 4100/9300) run multiple
independent FTD "container instances," each managed as its own logical device in FMC.

**GUI path:** Devices > Device Management > device > **More (⋮) > Convert to Multi-Instance**
(single device) or select multiple devices and **Select Bulk Action > Convert to
Multi-Instance** — since 7.6.0 you no longer need the chassis CLI to do this conversion.

```bash
# FTD CLI (multi-instance network setup, when needed manually):
configure multi-instance network ipv4 ...
configure multi-instance network ipv6 ...

# FXOS CLI (chassis level):
create device-manager
set deploymode
```

Chassis-level OS/firmware upgrades are separate from per-instance FTD software upgrades —
plan both phases when upgrading multi-instance hardware.

---

## 6. Device templates (zero-touch provisioning)

Since 7.6.0: pre-provision branch device configs (interfaces, basic policy) and apply them at
scale, including cloning settings from existing devices.

**GUI path:** Devices > **Template Management**.
- Supported platforms: Firepower 1000/2100 (FTD 7.4.1–7.4.x only), Secure Firewall 1200/3100.
- A device template can configure a device as a VPN **spoke**, not a hub.
- Pairs well with serial-number zero-touch registration for bulk branch rollouts.

---

## 7. Out-of-band change detection (7.7.0)

When emergency changes are made at the FTD CLI via `configure recovery-config` (see the CLI
reference doc) while the device is disconnected from FMC, reconnecting does **not** silently
adopt them.

**GUI path:** Devices > Device Management > device > **Health > Out of Band Status**.
Review the diff, acknowledge it, then manually reproduce the same change in FMC's normal
policy/object configuration before your next deploy — otherwise the next deploy will revert
the device to FMC's last-known configuration and undo the emergency fix.

Note: "Sync Interfaces" (renamed from "Sync Device" in 7.7.0) only pulls in *interface-level*
out-of-band changes; everything else (NAT, manager-access changes) goes through the Health >
Out of Band Status flow instead.
