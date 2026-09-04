# FMC 7.7.0 — Troubleshooting, Health Monitoring, Upgrade

Covers: packet-tracer, captures, health monitor modules, disk space, upgrade workflow
(FMC and FTD), RADKit remote TAC support.

## Table of Contents
1. Packet-level troubleshooting
2. Health monitor (7.7.0 changes)
3. Disk space management
4. Upgrade workflow — FMC
5. Upgrade workflow — FTD / chassis
6. RADKit (remote TAC support)
7. General troubleshooting CLI toolkit

---

## 1. Packet-level troubleshooting

**`packet-tracer`** is the single best "why isn't this working" tool on FTD — it simulates a
packet through the full inspection/NAT/routing pipeline and reports exactly where it would be
permitted, dropped, or altered.

```bash
packet-tracer input <ifc_name> tcp <src_ip> <src_port> <dst_ip> <dst_port>
packet-tracer input <ifc_name> pcap <pcap_filename> [honor-timestamp]   # replay a PCAP (7.6.0+)
show packet-tracer pcap trace [export-pcapng]                          # save trace as PCAP for Wireshark
```

**7.6.0+ packet tracer improvements (apply on 7.7.0):**
- Capture and replay **identity trace data** (requires Snort 3).
- Replay trace data on **NAT-configured devices**.
- Replay with **realistic timing** (`honor-timestamp` keyword).
- **Save trace output as a PCAP file** viewable in Wireshark (`export-pcapng`).

**Captures:**

```bash
capture <name> interface <ifc> match <protocol> <src_ip> <src_port> <dst_ip> <dst_port>
show capture <name>
show capture <name> detail
no capture <name>
```

**GUI path:** Troubleshooting > Tools > Packet Tracer (or launch directly from the Unified
Event Viewer for a specific connection — carried over from earlier versions).

---

## 2. Health monitor (7.7.0 changes)

**GUI path:** System/Administration > Health > **Policy** (define which modules alert and at
what thresholds) and Health > **Monitor** (live dashboard).

**New health modules in 7.7.0:**
- **Certificate Monitoring** — alerts before service authentication certificates expire on
  FMC and managed devices. Genuinely useful for Omar given his cert-management workload
  elsewhere (F5/FortiGate) — recommend enabling this.
- **MonetDB Statistics** — FMC's event database (MonetDB) health: size, active connections,
  memory use, data requests processed, slow-running requests. Enabled by default on new/
  upgraded FMCs; best practice is to leave it enabled.
- (10.0.0, for context only) Event datastore alerts extend this module to warn on zero active
  DB connections — not present on 7.7.0 itself.

**Continuous readiness checks (7.7.0):** for upgrades *from* 7.7.0+, you no longer manually
run a separate pre-upgrade readiness check — the system runs it continuously and surfaces
issues in the health monitor ahead of time. Supporting this:
- New **Database** module (devices) — monitors DB schema/config data integrity.
- New **FXOS Health** module (devices) — monitors the FXOS httpd service on FXOS-based
  hardware.
- **Disk Status** module is now more robust — daily `smartctl` runs feed disk-health alerts.

Devices still on pre-7.7 code continue to need the old in-upgrade manual readiness check when
targeting 7.7+.

---

## 3. Disk space management

**GUI path:** System/Administration > Health > Monitor > **Disk Usage** widget > **Clear disk
space** button (new in 7.7.0) — safely removes old backups, content updates, and
troubleshooting files in one click, rather than manually hunting for what's safe to delete.

```bash
# CLI visibility:
show disk-manager               # per-category breakdown

# Expert mode (only if the GUI utility isn't sufficient — see cli-administration.md
# for cautions about expert mode):
expert
df -h
du -sh /ngfw/var/*   # path varies by appliance/version
```

Low disk space can block upgrades, degrade performance, and (worst case) risk deleting
important files if you resort to manual cleanup under pressure — use the GUI utility first.

---

## 4. Upgrade workflow — FMC

**GUI path:** System/Administration > **Product Upgrades**.

Key 7.7.0-era behaviors:
- **No manual readiness check required** for FMC upgrades **from** 7.7.0+ — continuous
  checks via the health monitor replace it (see section 2). Pre-7.7 FMCs still need the
  in-upgrade manual check.
- **SRU update moved out of the upgrade itself.** After the FMC reboots post-upgrade to
  7.7+, wait for the SRU (Snort 2 intrusion rule package) to finish installing before adding
  devices, updating rules, or deploying — even if you manage zero Snort 2 devices, this
  step still runs.
- **Skip post-upgrade deploy in many cases** — after upgrading FMC, Snort 3 devices often
  don't need a manual deploy afterward. You *do* still need to deploy if: the upgrade updated
  the LSP and scheduled LSP updates are off; LSP updates are on but auto-redeploy is off;
  or specific changed configurations require it. If you plan to upgrade managed devices
  immediately after the FMC upgrade, you must deploy first regardless.
- **HA pairs:** most of the historical manual toil (copying packages to both peers, running
  readiness checks twice, pausing/resuming sync, resolving split-brain) is automated as of
  7.6.0+. You still log into the standby peer to kick off its own upgrade step.
- Auto-download of **new upgrade scripts** for the FMC itself, fixing late-breaking upgrade
  issues without needing a whole new upgrade package — happens transparently if internet
  access allows it (`cdo-ftd-images.s3-us-west-2.amazonaws.com`); if FMC can't reach it, the
  upgrade proceeds without the newer scripts.

Always take a fresh **backup** before starting (see cli-administration.md section 4).

---

## 5. Upgrade workflow — FTD / chassis

**GUI path:** Devices > **Threat Defense Upgrade** (per-device software) and Devices >
**Chassis Upgrade** (FXOS/firmware, for chassis-based platforms).

- Same "no manual readiness check needed" behavior applies for devices already on 7.7.0+.
- **Snort 2 devices cannot upgrade to 7.7.0+** — migrate to Snort 3 first (see
  intrusion-malware-decryption.md section 1).
- **Configuration change reports**: generate/download directly from the Threat Defense
  Upgrade or Chassis Upgrade wizards (Devices > Threat Defense Upgrade > **Configuration
  Changes**, or Devices > Chassis Upgrade > Configuration Changes) as long as you haven't
  cleared the upgrade workflow — no need to go through the old Advanced Deploy + Message
  Center download path unless you cleared the workflow or want to batch multiple devices.
- **Devices with internet access can download upgrade packages directly** (from 7.6.1),
  instead of always pulling from FMC — saves FMC disk space and transfer time. Devices try:
  internal server (if configured) → internet (if 7.6+/chassis 7.4.1+ and internet-capable) →
  FMC as fallback. Not supported for hotfixes.

```bash
# FTD CLI post-upgrade sanity checks:
show version
show failover state        # if HA, confirm both peers healthy post-upgrade
show cluster info           # if clustered
```

---

## 6. RADKit (remote TAC support) — new in 7.7.0

**GUI path:** Troubleshooting > Tools > **Remote Diagnostics** > Enable the RADKit service.

Cisco RADKit lets TAC engineers remotely connect into your deployment (including sudo-level
access when needed) for hands-on troubleshooting — **you control which appliances and for
how long**, and you retain access to the same diagnostic data/logs they see. Worth
mentioning to Omar as an option for escalations rather than screen-sharing or emailing logs
back and forth, though he may want to weigh this against ministry data-handling policy before
enabling it.

---

## 7. General troubleshooting CLI toolkit

```bash
# Connectivity
ping <ip>
traceroute <ip>

# Packet-level
packet-tracer input <ifc> tcp <src_ip> <src_port> <dst_ip> <dst_port>
capture <name> interface <ifc> match tcp <src> <dst>
show capture <name>

# State
show conn
show nat
show xlate
show route
show access-list

# HA / Cluster
show failover
show failover state
show cluster info

# Snort / performance
system support appid-cpu-profiling status
system support appid-cpu-profiling dump
system support flow-ip-profiling start flow-ip-file <filename> all {enable|disable}  # 7.7.0

# Application-detector debug (connection-based troubleshooting, 7.6.0+)
debug packet-module appid <severity: 3|4|7>   # 3=error, 4=warning, 7=debug

# Disk / system
show disk-manager
show process tree
show version
```

For anything beyond this — deep packet inspection internals, kernel-level crashes, or
persistent mysteries — the next step is a device backup + RADKit/TAC engagement rather than
continued expert-mode digging.
