---
name: ubuntu-server-24
description: >
  Expert-level guide for Ubuntu Server 24.04 LTS (Noble Numbat) — kernel 6.8,
  systemd v255, Netplan v1.0, AppArmor 4. Use this skill for ANY task involving:
  system administration, package management (apt/snap), networking (Netplan, ip, ss),
  storage (LVM, ext4, xfs, mount, fdisk, parted), services (systemd, journalctl),
  security (UFW, SSH, AppArmor, fail2ban, sudo), users/groups/permissions, process
  management, performance monitoring, cron, bash scripting, firewall, certificates,
  or any Ubuntu/Debian CLI or GUI (Cockpit, GNOME) task.
  Always consult this skill before answering any Ubuntu Server question.
---

# Ubuntu Server 24.04 LTS — Noble Numbat
## Expert Reference Guide — Kernel 6.8 | systemd 255 | Netplan 1.0

---

## CRITICAL CONTEXT — 24.04 SPECIFICS

| Feature | Ubuntu 24.04 Detail |
|---|---|
| Kernel | Linux 6.8 (HWE available) |
| Init system | systemd v255.4 |
| Network config | Netplan v1.0 (backend: systemd-networkd for servers) |
| DNS resolver | systemd-resolved (stub: 127.0.0.53) |
| Firewall frontend | UFW (backend: nftables/iptables) |
| Security module | AppArmor 4 (baked into kernel — cannot fully disable without kernel param) |
| Package manager | APT + Snap |
| Default shell | bash 5.2 |
| Python | Python 3.12 (default) |
| SSH server | OpenSSH 9.6p1 |
| LTS support | April 2029 (standard) / 2034 (Ubuntu Pro) |

**AppArmor 24.04 NOTE:** AppArmor is now baked into the kernel.
Unprivileged user namespace restrictions are **enabled by default**.
This affects Docker, browsers, and container tools — they need AppArmor profiles.

---

## Reference Files — Load When Needed

| Topic | File | Load When |
|---|---|---|
| System Essentials | `references/system-essentials.md` | Files, users, packages (apt/snap), processes, cron, bash |
| Networking | `references/networking.md` | Netplan, ip/ss, DNS, routes, bonds, VLANs, networkctl |
| Storage & LVM | `references/storage.md` | LVM, disks, filesystems, mount, fdisk, parted, RAID |
| Services & Systemd | `references/services-systemd.md` | systemctl, journalctl, unit files, targets, timers |
| Security | `references/security.md` | UFW, SSH hardening, AppArmor, fail2ban, sudo, PAM |
| Monitoring | `references/monitoring.md` | top/htop, iostat, vmstat, netstat, sar, logs, alerts |
| GUI — Cockpit | `references/gui-cockpit.md` | Full Cockpit web GUI — all panels and procedures |
| Troubleshooting | `references/troubleshooting.md` | Boot issues, network, storage, service failures, recovery |

**Always read the relevant reference file before answering.**

---

## CLI Fundamentals (Always Available)

```bash
# System info
uname -r                    # kernel version
lsb_release -a              # Ubuntu version
hostnamectl                 # full host info + kernel + OS

# Package management
apt update && apt upgrade   # update system
apt install <pkg>           # install package
apt remove <pkg>            # remove package
apt search <keyword>        # search packages
dpkg -l | grep <pkg>        # check if installed

# Service management
systemctl status <service>  # check service
systemctl start|stop|restart|enable|disable <service>
journalctl -u <service> -f  # follow service logs

# Networking
ip addr show                # show IP addresses
ip route show               # show routing table
netplan apply               # apply network config
ufw status                  # firewall status

# System health
df -h                       # disk usage
free -h                     # memory usage
top                         # process monitor
uptime                      # load average
```

---

## Default Paths Quick Reference

```
Network config:    /etc/netplan/*.yaml
DNS (resolved):    /etc/systemd/resolved.conf
SSH config:        /etc/ssh/sshd_config
UFW rules:         /etc/ufw/
AppArmor profiles: /etc/apparmor.d/
Systemd units:     /etc/systemd/system/   (custom)
                   /lib/systemd/system/   (package)
Apt sources:       /etc/apt/sources.list.d/
Logs:              /var/log/  +  journalctl
Crontabs:          /etc/cron.d/  /var/spool/cron/crontabs/
Sudoers:           /etc/sudoers  (edit with visudo)
Users:             /etc/passwd  /etc/shadow  /etc/group
```
