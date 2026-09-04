# Monitoring & Performance — Ubuntu Server 24.04
## top, htop, iostat, vmstat, netstat, sar, Logs

---

## CPU & PROCESS MONITORING

```bash
# ── TOP ──
top                                 # interactive process monitor
top -d 2                            # refresh every 2 seconds
top -u nginx                        # show only nginx user processes
top -b -n 1                         # batch mode (one snapshot)
top -b -n 1 | head -20             # top 20 processes snapshot

# Top keyboard shortcuts:
# P — sort by CPU (default)
# M — sort by memory
# T — sort by time
# k — kill process (enter PID)
# r — renice process
# f — field select
# 1 — toggle per-CPU view
# q — quit
# z — color mode
# H — show threads

# ── HTOP (Enhanced top) ──
sudo apt install htop
htop                                # interactive with colors
htop -u www-data                    # filter by user
htop -d 5                           # 500ms delay

# htop shortcuts:
# F2 — setup/config
# F3 — search
# F4 — filter
# F5 — tree view
# F6 — sort
# F7/F8 — nice/renice
# F9 — kill
# F10 — quit

# ── CPU STATS ──
mpstat 1 5                          # per-CPU stats, 1s interval, 5 times
mpstat -P ALL 1                     # all CPUs, every 1s
sar -u 1 10                         # CPU usage, 1s interval, 10 samples
sar -u -f /var/log/sysstat/sa$(date +%d)  # historical CPU from sysstat

# Load average interpretation:
# uptime → load average: X.XX, X.XX, X.XX (1min, 5min, 15min)
# Load = 1.0 on 1-core = 100% busy
# Load = 2.0 on 4-core = 50% busy
# Load > number of CPU cores = overloaded

nproc                               # number of CPU cores
lscpu | grep "^CPU(s):"            # detailed CPU count
cat /proc/cpuinfo | grep processor | wc -l  # core count

# ── PROCESS DETAILS ──
cat /proc/<PID>/status              # process details
cat /proc/<PID>/cmdline             # command line (with null bytes)
ls -la /proc/<PID>/fd               # open file descriptors
lsof -p <PID>                       # files opened by process
strace -p <PID>                     # system calls (debug)
strace -c -p <PID>                  # summary of system calls
```

---

## MEMORY MONITORING

```bash
# ── MEMORY OVERVIEW ──
free -h                             # memory + swap (human readable)
free -h -s 2                        # refresh every 2 seconds
cat /proc/meminfo                   # detailed memory info
vmstat 1 10                         # virtual memory stats, 1s interval

# vmstat columns:
# r=running, b=blocked
# swpd=swap used, free=free RAM
# si=swap-in, so=swap-out (bad if non-zero constantly)
# bi=blocks-in, bo=blocks-out (disk I/O)
# us=user CPU, sy=system CPU, id=idle, wa=wait I/O

# ── MEMORY BY PROCESS ──
ps aux --sort=-%mem | head -20      # top memory users
ps aux --sort=-%cpu | head -20      # top CPU users
smem -r | head -20                  # accurate RSS+PSS (apt install smem)

# ── CACHE & BUFFERS ──
# "free" RAM = free + buff/cache (Linux uses RAM for cache)
# To free page cache (rarely needed):
sync && echo 1 | sudo tee /proc/sys/vm/drop_caches  # page cache
sync && echo 2 | sudo tee /proc/sys/vm/drop_caches  # dentries + inodes
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches  # all cache

# ── OOM KILLER ──
# Check if OOM killer was invoked:
dmesg | grep -i "oom\|killed"
journalctl -k | grep -i "oom\|killed"
grep -i "oom" /var/log/syslog

# Adjust OOM score for critical processes (lower = less likely to kill):
cat /proc/<PID>/oom_score
echo -500 | sudo tee /proc/<PID>/oom_score_adj  # protect process
echo  500 | sudo tee /proc/<PID>/oom_score_adj  # sacrifice first
```

---

## DISK I/O MONITORING

```bash
# ── IOSTAT ──
iostat                              # basic I/O stats
iostat -x 1 10                      # extended stats, 1s interval, 10 samples
iostat -d -h                        # human-readable
iostat -x /dev/sda 1               # specific disk, 1s interval

# Key iostat columns:
# %util — disk utilization (>90% = problem)
# await — average wait time for I/O (ms)
# r/s, w/s — reads/writes per second
# rMB/s, wMB/s — MB per second

# ── IOTOP ──
sudo apt install iotop
sudo iotop                          # interactive I/O monitor
sudo iotop -o                       # only active processes
sudo iotop -b -n 5                  # batch mode, 5 snapshots
sudo iotop -u www-data              # specific user I/O

# ── DSTAT (combined) ──
sudo apt install dstat
dstat                               # combined CPU + disk + net + mem
dstat -d                            # disk only
dstat -n                            # network only
dstat -c -d -n 1                    # CPU + disk + net, 1s

# ── DISK LATENCY ──
ioping /dev/sda                     # I/O latency test (apt install ioping)
ioping -c 10 /                      # 10 latency tests on /
```

---

## NETWORK MONITORING

```bash
# ── LIVE NETWORK ──
iftop -i enp0s3                     # live bandwidth per connection (apt install iftop)
iftop -n -i enp0s3                  # no DNS resolution
nethogs enp0s3                      # bandwidth per process (apt install nethogs)
nload enp0s3                        # simple bandwidth meter

# ── NETWORK STATS ──
ss -s                               # socket summary stats
ss -antp                            # all TCP connections
ss -anup                            # all UDP
netstat -s                          # protocol statistics

# Interface statistics:
ip -s link show enp0s3              # TX/RX bytes + errors
cat /proc/net/dev                   # raw interface stats
sar -n DEV 1 5                      # network device stats via sar

# ── NETWORK CONNECTIONS ──
ss -antp | grep ESTABLISHED | wc -l # count established TCP
ss -antp state time-wait | wc -l    # TIME_WAIT count (high = problem)
ss dst 192.168.1.1                  # connections to specific IP
lsof -i :80                         # processes using port 80
lsof -i TCP:22                      # SSH connections

# ── PACKET CAPTURE ──
sudo tcpdump -i enp0s3 -c 100       # capture 100 packets
sudo tcpdump -i enp0s3 port 80      # HTTP traffic
sudo tcpdump -i enp0s3 -w capture.pcap  # save to file
sudo tcpdump -r capture.pcap        # read saved capture
```

---

## LOG FILES & MONITORING

```bash
# ── KEY LOG FILES ──
/var/log/syslog                     # general system log
/var/log/auth.log                   # authentication + sudo
/var/log/kern.log                   # kernel messages
/var/log/dpkg.log                   # package installations
/var/log/apt/history.log            # apt install/remove history
/var/log/ufw.log                    # firewall log
/var/log/fail2ban.log               # fail2ban bans
/var/log/nginx/access.log           # nginx access
/var/log/nginx/error.log            # nginx errors
/var/log/mysql/error.log            # MySQL errors
/var/log/postgresql/                # PostgreSQL logs

# ── VIEWING LOGS ──
tail -f /var/log/syslog             # follow system log
tail -100 /var/log/auth.log         # last 100 lines
grep -i "error" /var/log/syslog | tail -50
grep "$(date +%b\ %e)" /var/log/syslog  # today's entries

# ── JOURNALCTL (preferred on 24.04) ──
journalctl -f                       # follow all logs
journalctl -p err -b                # all errors this boot
journalctl -u nginx -f              # follow nginx logs
journalctl -k -b -1                 # previous boot kernel msgs
journalctl --since "1 hour ago" -p warning  # warnings + last hour

# ── LOG ROTATION ──
# Config: /etc/logrotate.conf + /etc/logrotate.d/
cat /etc/logrotate.d/nginx          # example nginx rotation config
sudo logrotate -d /etc/logrotate.conf  # dry run
sudo logrotate -f /etc/logrotate.conf  # force rotation now

# ── SAR (System Activity Reporter) ──
sudo apt install sysstat
sudo systemctl enable --now sysstat

sar -u 1 10                         # CPU usage
sar -r 1 10                         # memory usage
sar -b 1 10                         # I/O stats
sar -n DEV 1 10                     # network stats
sar -q 1 10                         # queue length (load)
sar -A                              # all stats

# Historical data (from /var/log/sysstat/):
sar -u -f /var/log/sysstat/sa$(date +%d)      # today
sar -u -f /var/log/sysstat/sa$(date +%d -d "1 day ago")  # yesterday

# ── MONITORING DASHBOARDS ──
# Cockpit (web GUI — see gui-cockpit.md):
sudo apt install cockpit
sudo systemctl enable --now cockpit
# Access: https://SERVER-IP:9090

# Netdata (real-time web dashboard):
wget -O /tmp/netdata-kickstart.sh https://get.netdata.cloud/kickstart.sh
sudo bash /tmp/netdata-kickstart.sh
# Access: http://SERVER-IP:19999

# Prometheus + Grafana (enterprise monitoring):
# Install node_exporter for system metrics
sudo apt install prometheus-node-exporter
sudo systemctl enable --now prometheus-node-exporter
# Metrics at: http://SERVER-IP:9100/metrics
```

---

## PERFORMANCE QUICK DIAGNOSTICS

```bash
# ── FULL SYSTEM SNAPSHOT ──
echo "=== UPTIME ===" && uptime
echo "=== CPU ===" && mpstat 1 3
echo "=== MEMORY ===" && free -h
echo "=== TOP PROCESSES ===" && ps aux --sort=-%cpu | head -10
echo "=== DISK ===" && df -h && iostat -x 1 3
echo "=== NETWORK ===" && ss -s
echo "=== LISTENING PORTS ===" && ss -lntp
echo "=== FAILED SERVICES ===" && systemctl --failed

# ── QUICK BOTTLENECK CHECK ──
# High CPU?
top -> P  # sort by CPU, identify process
ps aux --sort=-%cpu | head -5

# High Memory?
free -h    # check if swap is being used
ps aux --sort=-%mem | head -5

# Disk I/O slow?
iostat -x 1 5 | grep -v "^$"   # look for high %util and await

# Network saturated?
iftop -i enp0s3                 # see per-connection bandwidth

# Disk space?
df -h      # check all filesystems
du -sh /var/* | sort -rh | head  # find what's using space
```
