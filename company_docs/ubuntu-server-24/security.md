# Security — Ubuntu Server 24.04
## UFW, SSH, AppArmor, fail2ban, sudo, Users

---

## UFW — UNCOMPLICATED FIREWALL

```bash
# ── STATUS ──
sudo ufw status                     # basic status
sudo ufw status verbose             # detailed + rules
sudo ufw status numbered            # numbered rules (for deletion)
sudo ufw show added                 # rules that have been added
sudo ufw show listening             # listening ports

# ── ENABLE / DISABLE ──
sudo ufw enable                     # enable firewall
sudo ufw disable                    # disable firewall
sudo ufw reset                      # reset all rules (CAREFUL!)

# ── DEFAULT POLICIES ──
sudo ufw default deny incoming      # block all incoming (recommended)
sudo ufw default allow outgoing     # allow all outgoing
sudo ufw default deny outgoing      # block all outgoing (restrictive)

# ── ALLOW RULES ──
sudo ufw allow ssh                  # allow SSH (port 22)
sudo ufw allow 22/tcp               # same as above
sudo ufw allow 22                   # TCP + UDP port 22
sudo ufw allow 80/tcp               # HTTP
sudo ufw allow 443/tcp              # HTTPS
sudo ufw allow 8080:8090/tcp        # port range
sudo ufw allow from 192.168.1.0/24  # allow from subnet
sudo ufw allow from 192.168.1.100   # allow from specific IP
sudo ufw allow from 192.168.1.100 to any port 22  # specific IP to specific port
sudo ufw allow in on enp0s3 to any port 80  # specific interface

# With comments (recommended):
sudo ufw allow 80/tcp comment 'HTTP web server'
sudo ufw allow 443/tcp comment 'HTTPS web server'
sudo ufw allow from 10.0.0.0/8 to any port 22 comment 'SSH from internal'

# ── DENY RULES ──
sudo ufw deny 23                    # block telnet
sudo ufw deny from 45.33.32.156     # block specific IP
sudo ufw deny from 45.33.32.0/24   # block IP range
sudo ufw deny out to 192.168.1.50  # block outgoing to IP

# ── LIMIT (Rate limiting for brute force protection) ──
sudo ufw limit ssh                  # limit SSH connections (6 per 30s)
sudo ufw limit 22/tcp               # same

# ── DELETE RULES ──
sudo ufw status numbered            # get rule numbers
sudo ufw delete 5                   # delete rule #5
sudo ufw delete allow 80/tcp        # delete by rule specification

# ── RELOAD / LOGGING ──
sudo ufw reload                     # reload rules
sudo ufw logging on                 # enable logging
sudo ufw logging medium             # log level: off|low|medium|high|full
# Logs: /var/log/ufw.log

# ── APPLICATION PROFILES ──
sudo ufw app list                   # list available app profiles
sudo ufw app info Nginx             # show app profile
sudo ufw allow 'Nginx Full'         # HTTP + HTTPS
sudo ufw allow 'Nginx HTTP'         # HTTP only
sudo ufw allow 'OpenSSH'            # SSH

# App profiles location: /etc/ufw/applications.d/
```

---

## SSH HARDENING

```bash
# SSH config file: /etc/ssh/sshd_config
# Ubuntu 24.04: also check /etc/ssh/sshd_config.d/*.conf

# Test config before applying:
sudo sshd -t                        # syntax check
sudo sshd -T | grep -i passwordauth # check effective config

# Reload after changes (no connection drop):
sudo systemctl reload ssh

# Restart (drops existing connections):
sudo systemctl restart ssh
```

### Recommended sshd_config settings
```ini
# /etc/ssh/sshd_config

Port 22                          # change to non-standard port if needed
AddressFamily inet               # IPv4 only (or: inet6, any)
ListenAddress 0.0.0.0            # or specific interface IP

# Authentication
PermitRootLogin no               # NEVER allow root login
PasswordAuthentication no        # force key-based auth only
PubkeyAuthentication yes         # enable key auth
AuthorizedKeysFile .ssh/authorized_keys
ChallengeResponseAuthentication no
UsePAM yes
PermitEmptyPasswords no
MaxAuthTries 3                   # lockout after 3 failed attempts
MaxSessions 10                   # max concurrent sessions

# User/Group restrictions
AllowUsers jsmith admin          # whitelist specific users
# OR:
AllowGroups sshlogin sudo        # whitelist groups
DenyUsers tempuser               # blacklist specific users

# Connection settings
ClientAliveInterval 300          # send keepalive every 5 min
ClientAliveCountMax 2            # disconnect after 2 missed keepalives
LoginGraceTime 30                # 30 seconds to authenticate
TCPKeepAlive yes

# Security features
X11Forwarding no                 # disable X11 (GUI) forwarding
AllowAgentForwarding no          # disable SSH agent forwarding
AllowTcpForwarding no            # disable TCP tunneling (or: yes for jumphosts)
PermitTunnel no
PrintLastLog yes
PrintMotd no

# Logging
LogLevel INFO                    # or: VERBOSE for debugging
SyslogFacility AUTH

# Cryptography (modern, secure defaults)
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,diffie-hellman-group16-sha512
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com
```

### SSH Key Management

```bash
# Generate SSH key pair (on client):
ssh-keygen -t ed25519 -C "admin@myserver"    # modern (recommended)
ssh-keygen -t rsa -b 4096 -C "admin@myserver" # RSA (older compatibility)

# Copy public key to server:
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@server
ssh-copy-id -i ~/.ssh/id_ed25519.pub -p 2222 user@server  # custom port

# Manual method:
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys

# Server: authorized_keys location
ls -la /home/user/.ssh/authorized_keys
cat /home/user/.ssh/authorized_keys

# SSH agent:
eval $(ssh-agent)               # start agent
ssh-add ~/.ssh/id_ed25519       # add key to agent
ssh-add -l                      # list keys in agent

# SSH config for client (/home/user/.ssh/config):
Host myserver
  HostName 192.168.1.100
  User admin
  Port 22
  IdentityFile ~/.ssh/id_ed25519
  ServerAliveInterval 60

# Restrict authorized_key to specific commands only:
# In ~/.ssh/authorized_keys:
command="/usr/bin/rsync --server",no-pty,no-agent-forwarding ssh-ed25519 AAAA...
```

---

## APPARMOR — APPLICATION SECURITY

```bash
# ── STATUS ──
sudo aa-status                      # full status (profiles + modes)
sudo apparmor_status                # alias
systemctl status apparmor           # service status

# ── PROFILE MODES ──
# enforce  — blocks + logs violations
# complain — logs violations only (no blocking) — good for testing
# disabled — no restrictions

# ── MANAGE PROFILES ──
sudo aa-enforce /usr/sbin/nginx     # set to enforce mode
sudo aa-complain /usr/sbin/nginx    # set to complain mode
sudo aa-disable /usr/sbin/nginx     # disable profile

# By profile name:
sudo aa-enforce nginx               # if profile name differs from binary

# ── VIEW PROFILES ──
ls /etc/apparmor.d/                 # profile directory
cat /etc/apparmor.d/usr.sbin.nginx  # view nginx profile

# ── LOAD / RELOAD PROFILES ──
sudo apparmor_parser -r /etc/apparmor.d/usr.sbin.nginx  # reload single profile
sudo systemctl reload apparmor      # reload all profiles
sudo aa-mergeprof /etc/apparmor.d/  # merge/update all profiles

# ── GENERATE PROFILE (for new application) ──
# Method 1: aa-genprof (interactive)
sudo aa-genprof /usr/bin/myapp      # run app, then press 's' to scan
# Then run the application, press 's' again when done, 'f' to finish

# Method 2: manually create profile
sudo nano /etc/apparmor.d/usr.bin.myapp
# Minimal profile:
cat > /etc/apparmor.d/usr.bin.myapp << 'EOF'
#include <tunables/global>
profile myapp /usr/bin/myapp {
  #include <abstractions/base>
  # Allow read to own binary
  /usr/bin/myapp mr,
  # Allow network
  network inet stream,
  network inet6 stream,
  # User namespace (24.04 requirement)
  userns,
}
EOF
sudo apparmor_parser -r /etc/apparmor.d/usr.bin.myapp

# ── 24.04 SPECIFIC: User Namespace Restrictions ──
# Check current restriction status
cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns

# Temporarily disable (one boot):
echo 0 | sudo tee /proc/sys/kernel/apparmor_restrict_unprivileged_userns

# Permanently disable (add to sysctl):
echo "kernel.apparmor_restrict_unprivileged_userns = 0" | \
  sudo tee /etc/sysctl.d/60-apparmor-namespace.conf
sudo sysctl --system

# ── LOGS ──
journalctl -f | grep apparmor      # live AppArmor events
grep -i apparmor /var/log/syslog   # AppArmor in syslog
grep "DENIED" /var/log/syslog | grep apparmor  # denied operations
sudo aa-notify -s 1 -v             # show AppArmor events (last 1 day)
```

---

## FAIL2BAN — BRUTE FORCE PROTECTION

```bash
# Install
sudo apt install fail2ban

# ── STATUS ──
sudo fail2ban-client status         # list all jails
sudo fail2ban-client status sshd    # specific jail status + banned IPs
sudo fail2ban-client ping           # check if running

# ── MANUAL BAN / UNBAN ──
sudo fail2ban-client set sshd banip 45.33.32.156   # ban IP manually
sudo fail2ban-client set sshd unbanip 45.33.32.156 # unban IP
sudo fail2ban-client set sshd unbanip ALL           # unban all

# ── RELOAD ──
sudo fail2ban-client reload         # reload config
sudo fail2ban-client reload sshd    # reload specific jail
sudo systemctl restart fail2ban     # full restart

# ── CONFIGURATION ──
# NEVER edit /etc/fail2ban/jail.conf directly
# Create: /etc/fail2ban/jail.local (overrides defaults)

cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime  = 1h          # ban duration
findtime = 10m         # time window for failures
maxretry = 5           # failures before ban
banaction = ufw        # use UFW for banning (preferred on Ubuntu)
backend = systemd      # use systemd journal

[sshd]
enabled = true
port    = 22
filter  = sshd
logpath = %(sshd_log)s
maxretry = 3
bantime  = 24h

[nginx-http-auth]
enabled = true
port    = http,https
filter  = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 5

[nginx-limit-req]
enabled = true
port    = http,https
filter  = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 10
EOF

sudo systemctl restart fail2ban

# ── LOGS ──
sudo tail -f /var/log/fail2ban.log  # fail2ban log
journalctl -u fail2ban -f           # via journalctl
```

---

## SECURITY AUDITING

```bash
# ── LYNIS (Security Audit Tool) ──
sudo apt install lynis
sudo lynis audit system             # full system audit
sudo lynis audit system --quick     # quick scan
# Report: /var/log/lynis.log
# Results: /var/log/lynis-report.dat

# ── CHECK OPEN PORTS ──
ss -lntp                            # listening TCP ports + process
ss -lnup                            # listening UDP ports
sudo nmap -sV localhost             # port scan localhost
sudo nmap -sV 192.168.1.100        # remote scan (authorized only)

# ── CHECK SUID/SGID FILES (security audit) ──
find / -perm /4000 -type f 2>/dev/null  # SUID files
find / -perm /2000 -type f 2>/dev/null  # SGID files

# ── CHECK WORLD-WRITABLE FILES ──
find / -perm -002 -type f 2>/dev/null

# ── CHECK LISTENING SERVICES ──
ss -lntp
systemctl list-units --type=service --state=running

# ── AUDIT LOG ──
sudo apt install auditd
sudo systemctl enable --now auditd
sudo auditctl -l                    # list audit rules
sudo ausearch -m LOGIN --start today  # today's login events
sudo ausearch -f /etc/passwd        # who accessed passwd
sudo aureport --summary             # audit summary report

# ── CHECK FAILED LOGINS ──
grep "Failed password" /var/log/auth.log | tail -20
grep "authentication failure" /var/log/auth.log | tail -20
journalctl -u ssh | grep -i "failed\|invalid" | tail -20
lastb | head -20                    # bad login attempts

# ── AUTOMATIC SECURITY UPDATES ──
sudo apt install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades  # enable via dialog
# Manual config: /etc/apt/apt.conf.d/50unattended-upgrades
# Check status:
systemctl status unattended-upgrades
sudo unattended-upgrade --dry-run --debug  # test run
```

---

## CERTIFICATES & TLS

```bash
# ── LET'S ENCRYPT (Certbot) ──
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d example.com -d www.example.com
sudo certbot renew --dry-run        # test renewal
sudo certbot renew                  # renew all certs
sudo certbot certificates           # list certificates

# Auto-renewal check:
systemctl list-timers | grep certbot
sudo systemctl status certbot.timer

# ── SELF-SIGNED CERTIFICATE ──
# Generate self-signed cert (for testing):
sudo openssl req -x509 -nodes -days 365 \
  -newkey rsa:4096 \
  -keyout /etc/ssl/private/selfsigned.key \
  -out /etc/ssl/certs/selfsigned.crt \
  -subj "/C=SA/ST=Riyadh/L=Riyadh/O=MyOrg/CN=myserver.domain.com"

# ── INSPECT CERTIFICATES ──
openssl s_client -connect domain.com:443 </dev/null  # view server cert
openssl x509 -in /etc/ssl/certs/cert.crt -text -noout  # view cert details
openssl x509 -in cert.crt -noout -dates  # expiry dates
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt cert.crt  # verify chain
```
