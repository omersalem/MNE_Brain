# Services & Systemd — Ubuntu Server 24.04
## systemctl, journalctl, Unit Files, Targets, Timers

---

## SYSTEMCTL — SERVICE MANAGEMENT

```bash
# ── STATUS ──
systemctl status nginx              # service status + recent logs
systemctl status nginx -l           # full log output (no truncation)
systemctl is-active nginx           # active / inactive (exit code: 0/1)
systemctl is-enabled nginx          # enabled / disabled
systemctl is-failed nginx           # failed / active/inactive
systemctl --failed                  # list all failed units
systemctl list-units --type=service # all loaded service units
systemctl list-units --type=service --state=running  # running only
systemctl list-unit-files           # all unit files + state
systemctl list-unit-files --type=service  # services only
systemctl list-unit-files --state=enabled # enabled services
systemctl list-dependencies nginx   # show dependencies

# ── START / STOP / RESTART ──
sudo systemctl start nginx          # start service
sudo systemctl stop nginx           # stop service
sudo systemctl restart nginx        # restart (stop + start)
sudo systemctl reload nginx         # reload config (no downtime when supported)
sudo systemctl reload-or-restart nginx  # reload if supported, else restart
sudo systemctl kill nginx           # send signal to service
sudo systemctl kill --signal=HUP nginx  # send specific signal

# ── ENABLE / DISABLE (boot persistence) ──
sudo systemctl enable nginx         # enable at boot
sudo systemctl enable --now nginx   # enable + start immediately
sudo systemctl disable nginx        # disable at boot
sudo systemctl disable --now nginx  # disable + stop immediately
sudo systemctl mask nginx           # mask (prevent any start)
sudo systemctl unmask nginx         # unmask

# ── RELOAD SYSTEMD ──
sudo systemctl daemon-reload        # reload after editing unit files
sudo systemctl daemon-reexec        # reexec systemd itself (rare)

# ── TARGETS (Runlevels) ──
systemctl get-default               # current default target
sudo systemctl set-default multi-user.target   # headless server
sudo systemctl set-default graphical.target    # desktop
sudo systemctl isolate rescue.target           # switch to rescue mode
sudo systemctl isolate emergency.target        # emergency shell

# Common targets:
# poweroff.target  — shutdown
# rescue.target    — single user
# multi-user.target — normal server (no GUI)
# graphical.target — GUI desktop
# reboot.target    — reboot

# ── POWER ──
sudo systemctl reboot               # reboot
sudo systemctl poweroff             # shutdown
sudo systemctl halt                 # halt (no power off)
sudo systemctl suspend              # suspend
sudo shutdown -h now                # immediate shutdown
sudo shutdown -r now                # immediate reboot
sudo shutdown -h +30                # shutdown in 30 minutes
sudo shutdown -r 02:00             # reboot at 2:00 AM
sudo shutdown -c                    # cancel scheduled shutdown
```

---

## CUSTOM SYSTEMD UNIT FILES

```ini
# /etc/systemd/system/myapp.service

[Unit]
Description=My Application
Documentation=https://example.com/docs
After=network.target network-online.target   # start after network
After=postgresql.service                     # start after postgres
Requires=postgresql.service                  # hard dependency
Wants=redis.service                          # soft dependency (optional)

[Service]
Type=simple            # simple | forking | oneshot | notify | dbus | idle
User=www-data
Group=www-data
WorkingDirectory=/opt/myapp

# Environment
Environment=NODE_ENV=production
Environment=PORT=3000
EnvironmentFile=/etc/myapp/env               # env file (KEY=VALUE per line)

# Commands
ExecStartPre=/usr/bin/test -f /opt/myapp/server.js  # pre-start check
ExecStart=/usr/bin/node /opt/myapp/server.js
ExecStartPost=/bin/echo "Started"
ExecStop=/bin/kill -TERM $MAINPID
ExecReload=/bin/kill -HUP $MAINPID

# Restart behavior
Restart=on-failure          # always | on-failure | on-abort | no
RestartSec=10               # wait 10s before restart
StartLimitIntervalSec=60    # limit restarts: only N times per interval
StartLimitBurst=3           # allow max 3 restarts per 60s

# Resource limits
LimitNOFILE=65536           # max open files
LimitNPROC=4096             # max processes
MemoryLimit=2G              # memory limit
CPUQuota=80%                # CPU limit

# Security hardening
NoNewPrivileges=yes
PrivateTmp=yes              # private /tmp
ProtectSystem=strict        # read-only /usr, /boot, /etc
ProtectHome=yes             # no access to /home
ReadWritePaths=/var/lib/myapp /var/log/myapp  # exceptions

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=myapp

[Install]
WantedBy=multi-user.target  # enable in: multi-user (server) or graphical
```

```bash
# Activate custom unit:
sudo systemctl daemon-reload
sudo systemctl enable --now myapp
sudo systemctl status myapp
```

---

## SERVICE TYPES EXPLAINED

```
Type=simple   — ExecStart is main process, systemd tracks it directly
Type=forking  — process forks to background (like traditional daemons)
               Set PIDFile=/var/run/myapp.pid
Type=oneshot  — runs once and exits (use for startup scripts)
               Add RemainAfterExit=yes to show as "active" after exit
Type=notify   — process sends sd_notify() when ready (complex but best)
Type=idle     — starts after all other jobs finish (low priority)
```

---

## JOURNALCTL — LOG MANAGEMENT

```bash
# ── BASIC VIEWING ──
journalctl                          # all logs (oldest first)
journalctl -r                       # reverse (newest first)
journalctl -f                       # follow (live tail)
journalctl -e                       # jump to end

# ── FILTER BY UNIT/SERVICE ──
journalctl -u nginx                 # logs for nginx
journalctl -u nginx -f              # follow nginx logs
journalctl -u nginx -u ssh          # multiple units
journalctl -u nginx --since today   # today's logs
journalctl -u nginx --since "1 hour ago"

# ── FILTER BY TIME ──
journalctl --since "2024-01-15"
journalctl --since "2024-01-15 09:00:00"
journalctl --since "2024-01-15" --until "2024-01-16"
journalctl --since yesterday
journalctl --since today
journalctl --since "1 hour ago"
journalctl --since "-30min"

# ── FILTER BY PRIORITY ──
journalctl -p err                   # errors only
journalctl -p warning               # warnings and above
journalctl -p 0..3                  # emerg to error
# Priorities: 0=emerg 1=alert 2=crit 3=err 4=warning 5=notice 6=info 7=debug

# ── FILTER BY BOOT ──
journalctl -b                       # current boot
journalctl -b -1                    # previous boot
journalctl -b -2                    # 2 boots ago
journalctl --list-boots             # list all boots

# ── KERNEL MESSAGES ──
journalctl -k                       # kernel messages (like dmesg)
journalctl -k -b -1                 # previous boot kernel messages
dmesg                               # kernel ring buffer
dmesg -T                            # with human-readable timestamps
dmesg -w                            # follow kernel messages
dmesg | grep -i error

# ── OUTPUT FORMAT ──
journalctl -u nginx -o json-pretty  # JSON format
journalctl -u nginx -o cat          # plain message only
journalctl -u nginx -o short        # default (timestamp + message)
journalctl -u nginx -o verbose      # all metadata fields
journalctl -n 50                    # last 50 lines

# ── DISK USAGE ──
journalctl --disk-usage             # journal disk space used
journalctl --vacuum-size=1G         # reduce to 1GB
journalctl --vacuum-time=2weeks     # remove logs older than 2 weeks
journalctl --vacuum-files=5         # keep only last 5 journal files

# ── JOURNAL CONFIG ──
# /etc/systemd/journald.conf
[Journal]
Storage=persistent          # persistent (across reboots) or volatile (RAM)
Compress=yes
SystemMaxUse=2G             # max disk space for journal
SystemKeepFree=1G           # minimum free space to keep
MaxRetentionSec=1month      # max age
ForwardToSyslog=no          # forward to syslog daemon

sudo systemctl restart systemd-journald  # apply config
```

---

## SYSTEMD TIMERS (Modern Cron)

```bash
# List all timers
systemctl list-timers               # active timers
systemctl list-timers --all         # all timers including inactive

# Example timer unit:
# /etc/systemd/system/mybackup.timer
[Unit]
Description=Run backup daily at 2 AM

[Timer]
OnCalendar=*-*-* 02:00:00          # daily at 2 AM
OnCalendar=weekly                   # every Sunday at midnight
OnCalendar=monthly                  # 1st of month at midnight
OnCalendar=Mon,Tue *-*-* 08:00:00  # Mon+Tue 8 AM
RandomizedDelaySec=15min            # random delay up to 15 min
Persistent=true                     # run if missed (e.g., system was off)

[Install]
WantedBy=timers.target

# /etc/systemd/system/mybackup.service
[Unit]
Description=Backup service

[Service]
Type=oneshot
ExecStart=/opt/scripts/backup.sh

# Activate timer:
sudo systemctl daemon-reload
sudo systemctl enable --now mybackup.timer
systemctl status mybackup.timer
```

---

## COMMON SERVICE MANAGEMENT PATTERNS

```bash
# ── NGINX ──
sudo systemctl enable --now nginx
sudo nginx -t                       # test config
sudo systemctl reload nginx         # reload config (no downtime)
sudo systemctl restart nginx        # full restart

# ── SSH ──
sudo systemctl status ssh           # note: "ssh" not "sshd" on Ubuntu
sudo sshd -t                        # test SSH config
sudo systemctl reload ssh           # reload without dropping connections
sudo systemctl restart ssh          # restart (drops connections!)

# ── MYSQL / MARIADB ──
sudo systemctl enable --now mysql
sudo mysql -u root                  # connect
sudo mysql_secure_installation      # post-install hardening

# ── POSTGRESQL ──
sudo systemctl enable --now postgresql
sudo -u postgres psql               # connect as postgres user

# ── DOCKER ──
sudo systemctl enable --now docker
docker ps                           # running containers
docker-compose up -d                # start compose stack

# ── UFW ──
sudo systemctl enable --now ufw
sudo ufw status verbose

# ── CHECK ALL FAILED SERVICES ──
systemctl --failed
journalctl -p err -b                # all errors this boot
```
