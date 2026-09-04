# Troubleshooting — Ubuntu Server 24.04
## Boot Issues, Network, Storage, Services, Recovery

---

## SYSTEM WON'T BOOT

```bash
# ── FROM GRUB MENU ──
# If boot fails: hold Shift or Esc during boot to get GRUB menu
# Select: "Advanced options for Ubuntu" → previous kernel version
# Or: "Ubuntu (recovery mode)"

# Recovery mode options:
#  resume       — continue normal boot
#  clean        — free disk space
#  dpkg         — repair broken packages
#  fsck         — check filesystems
#  grub         — update GRUB bootloader
#  network      — enable networking
#  root          — drop to root shell (no password needed!)

# ── FROM RECOVERY ROOT SHELL ──
# Remount root as read-write:
mount -o remount,rw /

# Check filesystem:
fsck -y /dev/sda1

# Check recent log:
journalctl -b -1 -p err            # previous boot errors

# Fix broken packages:
dpkg --configure -a
apt install -f

# ── KERNEL BOOT ISSUES ──
# Check available kernels:
ls /boot/vmlinuz*
# Boot old kernel from GRUB: Advanced → select older kernel

# Reinstall current kernel:
apt install --reinstall linux-image-$(uname -r)

# Update GRUB:
update-grub
```

---

## NETWORK TROUBLESHOOTING

```bash
# ── STEP BY STEP DIAGNOSIS ──

# Step 1: Check interface status
ip link show                        # are interfaces UP?
ip addr show                        # do they have IPs?

# Step 2: Check if it's a link issue (physical)
ip link show enp0s3 | grep "state UP"  # UP = cable connected

# Step 3: Check IP configuration
ip addr show enp0s3                 # has IP?
# If no IP and using DHCP:
sudo dhclient enp0s3                # request DHCP manually

# Step 4: Check routing
ip route show                       # default route present?
# "default via 192.168.1.1" should be there

# Step 5: Test local network
ping -c 3 192.168.1.1              # can reach gateway?
ping -c 3 8.8.8.8                  # can reach internet? (bypasses DNS)

# Step 6: Test DNS
ping -c 3 google.com               # DNS working?
resolvectl query google.com        # DNS resolution
resolvectl status                  # DNS server config

# Step 7: Check Netplan config
cat /etc/netplan/*.yaml            # correct config?
sudo netplan try                   # test config

# ── COMMON NETWORK PROBLEMS ──

# Problem: No IP address
ip addr show                        # no IP listed
sudo netplan apply                  # re-apply config
sudo dhclient enp0s3                # force DHCP request
sudo systemctl restart systemd-networkd  # restart network backend

# Problem: Cannot reach internet but gateway works
ip route show | grep default        # default route exists?
ping 8.8.8.8                        # internet bypassing DNS?
# If ping 8.8.8.8 works but ping google.com fails → DNS problem

# Problem: DNS not resolving
resolvectl status                   # check DNS servers
cat /etc/resolv.conf                # check resolv.conf
resolvectl flush-caches             # flush DNS cache
sudo systemctl restart systemd-resolved

# Problem: Interface not coming up after reboot
cat /etc/netplan/*.yaml             # check config
sudo netplan generate               # validate YAML
sudo netplan --debug apply          # verbose apply

# Problem: Network slow
iperf3 -c 192.168.1.1              # test throughput
ss -s                               # socket stats
netstat -s | grep -i "retransmit"  # TCP retransmits (packet loss)
ip -s link show enp0s3 | grep -E "RX|TX"  # interface errors
```

---

## SERVICE TROUBLESHOOTING

```bash
# ── FAILED SERVICE DIAGNOSIS ──

# Step 1: Check status
systemctl status nginx              # get error message
systemctl is-failed nginx           # is it in failed state?

# Step 2: Check logs
journalctl -u nginx -b -n 50       # last 50 lines this boot
journalctl -u nginx --since "10 minutes ago"
journalctl -xe | grep nginx        # recent errors with context

# Step 3: Test application config
nginx -t                            # nginx config test
apache2ctl configtest               # apache config test
sshd -t                             # ssh config test
mysql --defaults-file=/etc/mysql/my.cnf -e "SELECT 1"  # mysql test

# Step 4: Check dependencies
systemctl list-dependencies nginx   # what does nginx need?
systemctl status mysql              # is required service running?

# Step 5: Check resource issues
# Port conflict:
ss -lntp | grep :80                 # who is using port 80?
# Permission:
ls -la /var/www/html                # correct permissions?
ls -la /var/log/nginx/             # log file permissions?

# Step 6: Try starting manually with verbose output
sudo nginx -g "daemon off;"         # run in foreground
sudo -u www-data /usr/bin/php-fpm  # run as service user

# ── RESET FAILED STATE ──
sudo systemctl reset-failed nginx   # clear failed state
sudo systemctl start nginx          # try again

# ── COMMON SERVICE ERRORS ──

# Error: "Failed to bind socket: Address already in use"
ss -lntp | grep :80                 # find what's using the port
sudo kill $(lsof -t -i:80)         # kill process on port

# Error: "Permission denied"
ls -la /var/log/nginx/             # check log directory
sudo chown -R www-data:www-data /var/log/nginx/
sudo chmod 755 /var/log/nginx/

# Error: "Failed to start — systemd dependency"
systemctl status <dependency>      # check required service
journalctl -u <dependency> -b

# Service keeps restarting / crash loop:
journalctl -u myservice -f          # follow logs during crash
# Look for error before exit
systemctl edit myservice            # add restart delay:
# [Service]
# RestartSec=10
# StartLimitIntervalSec=60
# StartLimitBurst=3
```

---

## DISK & STORAGE TROUBLESHOOTING

```bash
# ── DISK FULL ──
df -h                               # which filesystem is full?
du -sh /var/* | sort -rh | head    # find what's using space in /var
du -sh /* 2>/dev/null | sort -rh | head -20  # top directories

# Common culprits:
du -sh /var/log/                    # log files
du -sh /var/cache/apt/              # apt cache
du -sh /tmp/                        # temp files
journalctl --disk-usage             # journal size

# Solutions:
sudo apt clean                      # clear apt cache
sudo apt autoremove                 # remove unused packages
sudo journalctl --vacuum-size=500M  # trim journal
sudo find /var/log -name "*.gz" -delete  # delete compressed old logs
sudo truncate -s 0 /var/log/largelogfile.log  # empty specific log

# ── FILESYSTEM ERRORS ──
dmesg | grep -i "error\|fail\|i/o"  # kernel I/O errors
journalctl -k | grep -i "error"     # kernel errors via journal

# Fix corrupted filesystem (must unmount first):
sudo umount /dev/sdb1               # unmount
sudo fsck -y /dev/sdb1             # auto-fix ext4/ext3/ext2
sudo xfs_repair /dev/sdb1          # XFS repair

# If cannot unmount (root filesystem):
# Boot into recovery mode → fsck option

# ── DISK PERFORMANCE ──
iostat -x 1 10                      # high %util or await?
iotop -o                            # which process is hammering disk?

# ── LVM ISSUES ──
# LV won't mount:
sudo vgscan                         # re-scan for VGs
sudo vgchange -ay                   # activate all VGs
sudo lvscan                         # check LV state
sudo lvchange -ay /dev/ubuntu-vg/data  # activate specific LV

# VG missing after disk replacement:
sudo pvscan                         # rescan PVs
sudo vgdisplay                      # show VG status
```

---

## PACKAGE MANAGEMENT TROUBLESHOOTING

```bash
# ── APT ERRORS ──

# Error: "dpkg was interrupted, you must manually run 'dpkg --configure -a'"
sudo dpkg --configure -a
sudo apt install -f                 # fix broken dependencies

# Error: "Package has unmet dependencies"
sudo apt install -f                 # auto-fix
sudo apt --fix-broken install

# Error: "Repository does not have a Release file" or GPG error
sudo apt update 2>&1 | grep -i "error\|warning"  # see which repo
# Remove bad repo:
sudo add-apt-repository --remove ppa:badrepo/ppa
# Or edit sources:
ls /etc/apt/sources.list.d/
sudo rm /etc/apt/sources.list.d/badrepo.list

# Error: "Could not get lock /var/lib/dpkg/lock"
# Another apt process is running
ps aux | grep apt                   # find the process
sudo lsof /var/lib/dpkg/lock       # who has the lock?
# Wait for it to finish, or if stuck:
sudo kill <PID>
sudo rm /var/lib/dpkg/lock*
sudo rm /var/lib/apt/lists/lock
sudo dpkg --configure -a

# ── SNAP ISSUES ──
snap list                           # list installed snaps
snap changes                        # recent snap operations
snap abort <task-id>                # abort stuck task
sudo systemctl restart snapd        # restart snap daemon
```

---

## SSH TROUBLESHOOTING

```bash
# ── CANNOT SSH INTO SERVER ──

# From client (verbose):
ssh -v user@server                  # verbose (shows each step)
ssh -vvv user@server                # very verbose

# Check server side:
sudo systemctl status ssh           # is SSH running?
ss -lntp | grep :22                 # is port 22 listening?
sudo ufw status | grep 22           # is port allowed in firewall?
sudo journalctl -u ssh --since "5 minutes ago"  # SSH logs

# ── COMMON SSH ERRORS ──

# Error: "Connection refused"
sudo systemctl start ssh            # start SSH
ss -lntp | grep :22                 # verify listening
sudo ufw allow 22/tcp               # allow in firewall

# Error: "Permission denied (publickey)"
ls -la ~/.ssh/                      # check permissions
# Should be: drwx------ .ssh/
# Should be: -rw------- authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
# Check if key is in authorized_keys:
cat ~/.ssh/authorized_keys
# Check sshd_config:
grep PubkeyAuthentication /etc/ssh/sshd_config

# Error: "Host key verification failed"
# Remove old key from known_hosts:
ssh-keygen -R server-ip             # on client
# Or manually edit: ~/.ssh/known_hosts

# Locked out (password auth disabled, lost key):
# Access via console (cloud provider web console)
# Then: add new public key to ~/.ssh/authorized_keys
# Or: temporarily enable password auth, fix keys, re-disable

# SSH too slow to connect:
# UseDNS no  → add to /etc/ssh/sshd_config
# GSSAPIAuthentication no → add to /etc/ssh/sshd_config
```

---

## HIGH CPU / MEMORY ISSUES

```bash
# ── HIGH CPU ──
top                                 # press P to sort by CPU
ps aux --sort=-%cpu | head -10      # top CPU processes
# Identify process → check what it's doing:
strace -p <PID> -c                  # system call summary
lsof -p <PID>                       # files the process has open

# If it's a known service:
journalctl -u service-name -f      # check for errors causing loop
# If unknown:
cat /proc/<PID>/cmdline | tr '\0' ' '  # get full command

# ── HIGH MEMORY ──
free -h                             # check if swap is being used
ps aux --sort=-%mem | head -10      # top memory consumers
# If swap is heavy → OOM likely incoming
dmesg | grep -i oom                 # OOM killer events

# ── ZOMBIE PROCESSES ──
ps aux | grep defunct               # find zombies
# Zombies can't be killed directly — kill parent:
ps -o ppid= <zombie-PID>           # get parent PID
kill <parent-PID>                  # kill parent

# ── STUCK PROCESS ──
# Regular kill (SIGTERM — graceful):
sudo kill <PID>
# Force kill (SIGKILL):
sudo kill -9 <PID>
# Verify killed:
ps aux | grep <PID>
```

---

## RECOVERY COMMANDS QUICK REFERENCE

| Problem | First Command |
|---|---|
| System won't boot | Boot recovery mode → root shell |
| No network | `ip addr show; ip route show; ping 8.8.8.8` |
| Service failed | `systemctl status service; journalctl -u service -b -n 50` |
| Disk full | `df -h; du -sh /var/* \| sort -rh` |
| Can't SSH in | `systemctl status ssh; ss -lntp \| grep :22; ufw status` |
| High CPU | `top → P; ps aux --sort=-%cpu \| head -10` |
| High memory | `free -h; ps aux --sort=-%mem \| head -10` |
| Package broken | `sudo dpkg --configure -a; sudo apt install -f` |
| Filesystem corrupt | `sudo fsck -y /dev/sdb1` (unmounted) |
| LVM not active | `sudo vgscan; sudo vgchange -ay` |
| DNS broken | `resolvectl flush-caches; systemctl restart systemd-resolved` |
| AppArmor blocking | `dmesg \| grep apparmor; sudo aa-complain /path/to/app` |
