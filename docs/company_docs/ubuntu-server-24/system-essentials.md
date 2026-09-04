# System Essentials — Ubuntu Server 24.04
## Files, Users, Packages, Processes, Cron, Bash

---

## SYSTEM INFORMATION

```bash
# Full system info
uname -a                        # kernel + arch + hostname
uname -r                        # kernel version only
lsb_release -a                  # Ubuntu release info
hostnamectl                     # hostname, OS, kernel, arch, virtualization
cat /etc/os-release             # detailed OS info
uptime                          # uptime + load averages
uptime -p                       # human readable uptime

# Hardware info
lscpu                           # CPU details, cores, threads
lsmem                           # memory layout
lspci                           # PCI devices
lsusb                           # USB devices
lsblk                           # block devices (disks/partitions)
lsblk -f                        # with filesystem type and UUID
dmidecode -t system             # DMI/BIOS system info (needs sudo)
dmidecode -t memory             # RAM DIMM info

# Set hostname
hostnamectl set-hostname myserver
# Edit /etc/hosts if needed:
nano /etc/hosts
# Add: 127.0.1.1   myserver

# Timezone
timedatectl                     # current time + timezone + NTP status
timedatectl list-timezones | grep Asia
timedatectl set-timezone Asia/Riyadh
timedatectl set-ntp true        # enable NTP sync

# Locale
locale                          # current locale settings
localectl                       # system locale + keyboard
localectl set-locale LANG=en_US.UTF-8
```

---

## PACKAGE MANAGEMENT — APT

```bash
# ── REPOSITORY UPDATE ──
apt update                          # refresh package index
apt upgrade                         # upgrade installed packages
apt full-upgrade                    # upgrade + handle dependencies
apt dist-upgrade                    # same as full-upgrade
apt update && apt upgrade -y        # non-interactive full update
unattended-upgrade                  # run automatic upgrades manually

# ── INSTALL / REMOVE ──
apt install nginx                   # install package
apt install -y nginx curl wget      # install multiple, no prompt
apt install ./package.deb           # install local .deb file
apt remove nginx                    # remove (keep config)
apt purge nginx                     # remove + config files
apt autoremove                      # remove orphaned dependencies
apt clean                           # clear downloaded package cache
apt autoclean                       # remove only outdated cached packages

# ── SEARCH & INFO ──
apt search nginx                    # search by keyword
apt show nginx                      # package details
apt list --installed                # list installed packages
apt list --installed | grep nginx   # check specific package
apt list --upgradable               # list upgradable packages
dpkg -l                             # list all installed (dpkg level)
dpkg -l | grep nginx                # check specific
dpkg -L nginx                       # list files installed by package
dpkg -S /usr/sbin/nginx             # which package owns a file
dpkg --get-selections               # all installed packages

# ── SOURCES / REPOSITORIES ──
# Add repository
add-apt-repository ppa:user/repo
add-apt-repository universe         # enable universe component
# Manual source:
nano /etc/apt/sources.list.d/myrepo.list
# Add: deb [signed-by=/usr/share/keyrings/myrepo.gpg] https://repo.example.com jammy main

# Add GPG key (modern method)
curl -fsSL https://repo.example.com/gpg.key | \
  gpg --dearmor -o /usr/share/keyrings/myrepo.gpg

# ── HOLD / UNHOLD PACKAGE VERSION ──
apt-mark hold nginx                 # prevent nginx from being upgraded
apt-mark unhold nginx               # allow upgrades again
apt-mark showhold                   # show held packages

# ── AUTOMATIC UPDATES ──
apt install unattended-upgrades
dpkg-reconfigure unattended-upgrades   # configure via dialog
# Config file: /etc/apt/apt.conf.d/50unattended-upgrades
```

---

## PACKAGE MANAGEMENT — SNAP

```bash
snap find nginx                     # search snap store
snap install nginx                  # install snap
snap install --classic code         # install with classic confinement
snap list                           # list installed snaps
snap info nginx                     # package details + versions
snap refresh                        # update all snaps
snap refresh nginx                  # update specific snap
snap remove nginx                   # remove snap
snap remove --purge nginx           # remove + data

snap services                       # list snap services
snap start nginx                    # start snap service
snap stop nginx                     # stop snap service
snap restart nginx                  # restart
snap logs nginx                     # view snap logs
snap logs nginx -f                  # follow snap logs

snap connections nginx              # show snap interfaces/connections
snap connect nginx:network-bind     # connect interface
```

---

## FILE SYSTEM OPERATIONS

```bash
# ── NAVIGATION ──
pwd                                 # current directory
ls -la                              # list all with details
ls -lah                             # with human-readable sizes
ls -lt                              # sort by time (newest first)
ls -lS                              # sort by size
tree /etc -L 2                      # tree view, 2 levels deep
cd /path/to/dir                     # change directory
cd -                                # go back to previous directory
cd ~                                # go to home directory

# ── FILE OPERATIONS ──
cp file.txt /dest/                  # copy file
cp -r /src/ /dest/                  # copy directory recursively
cp -rp /src/ /dest/                 # preserve permissions + timestamps
mv file.txt /dest/                  # move/rename
rm file.txt                         # delete file
rm -rf /path/                       # delete directory (DANGEROUS)
mkdir -p /path/to/dir               # create directory + parents
touch file.txt                      # create empty file / update timestamp
ln -s /target /link                 # create symlink
ln /target /hardlink                # create hard link
readlink -f /symlink                # resolve symlink path

# ── FIND ──
find /etc -name "*.conf"            # find files by name
find /var/log -name "*.log" -mtime -1  # modified in last 1 day
find / -size +100M -type f          # files larger than 100MB
find /home -user jsmith             # files owned by user
find / -perm /4000 -type f          # SUID files (security audit)
find /etc -name "*.conf" -exec grep -l "password" {} \;  # find + exec

# ── SEARCH IN FILES ──
grep "error" /var/log/syslog        # search in file
grep -r "error" /var/log/           # recursive search
grep -rn "error" /var/log/          # with line numbers
grep -i "ERROR" /var/log/syslog     # case insensitive
grep -v "DEBUG" /var/log/syslog     # invert match (exclude)
grep -E "error|warn" /var/log/syslog # regex: multiple patterns

# ── TEXT PROCESSING ──
cat file.txt                        # print file
head -20 file.txt                   # first 20 lines
tail -20 file.txt                   # last 20 lines
tail -f /var/log/syslog             # follow log (live)
less /var/log/syslog                # page through file (q to quit)
wc -l file.txt                      # count lines
sort file.txt                       # sort lines
sort -u file.txt                    # sort + unique
awk '{print $1}' file.txt           # print first field
sed 's/old/new/g' file.txt         # replace text
cut -d: -f1 /etc/passwd             # cut by delimiter

# ── COMPRESSION ──
tar -czf archive.tar.gz /path/      # create gzip tar
tar -cjf archive.tar.bz2 /path/    # create bzip2 tar
tar -xzf archive.tar.gz            # extract gzip tar
tar -xzf archive.tar.gz -C /dest/  # extract to specific dir
tar -tzf archive.tar.gz            # list contents
zip -r archive.zip /path/          # create zip
unzip archive.zip                  # extract zip
unzip archive.zip -d /dest/        # extract to dir
gzip file.txt                      # compress (creates file.txt.gz)
gunzip file.txt.gz                 # decompress

# ── PERMISSIONS ──
chmod 755 file.sh                  # rwxr-xr-x
chmod 644 file.conf                # rw-r--r--
chmod +x script.sh                 # add execute bit
chmod -R 755 /path/               # recursive
chown user:group file.txt          # change owner + group
chown -R www-data:www-data /var/www/  # recursive chown
chgrp group file.txt               # change group only

# Permission notation:
# 4=read, 2=write, 1=execute
# 755 = rwxr-xr-x (owner: rwx, group: rx, others: rx)
# 644 = rw-r--r-- (owner: rw, group: r, others: r)
# 700 = rwx------ (owner only)
# 600 = rw------- (owner only, no execute)

# Special permissions
chmod u+s /usr/bin/program         # SUID (run as file owner)
chmod g+s /shared/dir              # SGID (new files inherit group)
chmod +t /tmp                      # sticky bit (only owner can delete)

# ── ACLs (Access Control Lists) ──
apt install acl
getfacl /path/file                 # view ACL
setfacl -m u:jsmith:rwx /path/    # grant user rwx
setfacl -m g:devteam:rx /path/    # grant group rx
setfacl -x u:jsmith /path/        # remove user ACL
setfacl -b /path/                  # remove all ACLs

# ── DISK USAGE ──
df -h                              # filesystem usage
df -h /var                         # specific filesystem
du -sh /var/log/                   # directory size
du -sh /var/log/* | sort -h       # sorted by size
du -h --max-depth=1 /var/          # 1 level deep
ncdu /var/                         # interactive disk usage browser
```

---

## USERS & GROUPS

```bash
# ── READ (Safe) ──
id                                  # current user UID/GID/groups
id jsmith                           # specific user info
whoami                              # current username
who                                 # logged in users
w                                   # logged in users + activity
last                                # login history
last jsmith                         # specific user history
lastlog                             # last login for all users
groups jsmith                       # groups for user
cat /etc/passwd                     # user accounts
cat /etc/group                      # groups
getent passwd jsmith                # user entry
getent group sudo                   # group members

# ── CREATE USERS ──
adduser jsmith                      # interactive (recommended)
useradd -m -s /bin/bash -c "John Smith" jsmith  # non-interactive
# Options: -m=create home, -s=shell, -c=comment, -g=primary group
# -G=supplementary groups, -d=home dir, -e=expiry date

# ── MODIFY USERS ──
usermod -aG sudo jsmith             # add to sudo group (-a = append!)
usermod -aG docker,www-data jsmith  # add to multiple groups
usermod -s /bin/bash jsmith         # change shell
usermod -l newname jsmith           # rename user
usermod -L jsmith                   # lock account (disable login)
usermod -U jsmith                   # unlock account
usermod -e 2025-12-31 jsmith        # set expiry date
usermod -d /new/home jsmith         # change home directory

# ── PASSWORDS ──
passwd jsmith                       # set/change password
passwd -l jsmith                    # lock password
passwd -u jsmith                    # unlock password
passwd -e jsmith                    # expire password (force change on next login)
chage -l jsmith                     # password aging info
chage -M 90 jsmith                  # max password age 90 days
chage -E 2025-12-31 jsmith          # account expiry date

# ── DELETE USERS ──
deluser jsmith                      # remove user (keep home)
deluser --remove-home jsmith        # remove user + home dir
deluser jsmith groupname            # remove user from group

# ── GROUPS ──
groupadd devteam                    # create group
groupmod -n newname devteam         # rename group
groupdel devteam                    # delete group
gpasswd -a jsmith devteam           # add user to group
gpasswd -d jsmith devteam           # remove user from group
gpasswd -M jsmith,mjones devteam    # set group members

# ── SUDO ──
visudo                              # edit sudoers safely
# /etc/sudoers.d/ — drop-in files (preferred)
echo "jsmith ALL=(ALL:ALL) ALL" > /etc/sudoers.d/jsmith
echo "jsmith ALL=(ALL) NOPASSWD: /usr/bin/systemctl" > /etc/sudoers.d/jsmith  # passwordless specific cmd
chmod 440 /etc/sudoers.d/jsmith

# Common sudo entries:
# jsmith ALL=(ALL:ALL) ALL              — full sudo
# %devteam ALL=(ALL:ALL) ALL           — group sudo
# jsmith ALL=(ALL) NOPASSWD: ALL       — no password (risky)
# jsmith ALL=(ALL) /usr/bin/apt, /sbin/reboot  — specific commands only
```

---

## PROCESS MANAGEMENT

```bash
# ── VIEW PROCESSES ──
ps aux                              # all processes (BSD style)
ps aux | grep nginx                 # filter by name
ps -ef                              # all processes (System V style)
ps -ef --forest                     # with parent-child tree
pgrep nginx                         # get PID by name
pgrep -a nginx                      # PID + command line
pidof nginx                         # PID(s) of process

# ── SIGNALS / KILL ──
kill <PID>                          # send SIGTERM (graceful stop)
kill -9 <PID>                       # send SIGKILL (force kill)
kill -HUP <PID>                     # SIGHUP (reload config)
kill -USR1 <PID>                    # SIGUSR1 (app-specific)
killall nginx                       # kill by name
pkill nginx                         # kill by pattern
pkill -u jsmith                     # kill all processes by user

# ── BACKGROUND / FOREGROUND ──
command &                           # run in background
jobs                                # list background jobs
fg %1                               # bring job 1 to foreground
bg %1                               # send job 1 to background
nohup command &                     # run immune to hangups
disown %1                           # detach job from shell

# ── PRIORITY ──
nice -n 10 command                  # run with lower priority (10)
nice -n -10 command                 # higher priority (needs sudo)
renice -n 15 -p <PID>              # change priority of running process

# ── MONITORING ──
top                                 # interactive process monitor
# Top shortcuts: P=sort CPU, M=sort MEM, k=kill, r=renice, q=quit
htop                                # enhanced top (install: apt install htop)
# htop shortcuts: F6=sort, F9=kill, F4=filter, F3=search
atop                                # advanced system monitor

# ── SCREEN / TMUX (Keep sessions alive) ──
# tmux (recommended):
tmux                                # new session
tmux new -s mysession               # named session
tmux ls                             # list sessions
tmux attach -t mysession            # attach to session
tmux kill-session -t mysession      # kill session
# Inside tmux: Ctrl+b then:
#   d = detach, c = new window, n/p = next/prev, % = split vertical
#   " = split horizontal, x = kill pane, [ = scroll mode

# screen:
screen                              # new screen
screen -S mysession                 # named session
screen -ls                         # list sessions
screen -r mysession                 # reattach
# Inside screen: Ctrl+a then d = detach
```

---

## SCHEDULED TASKS — CRON & SYSTEMD TIMERS

```bash
# ── CRON ──
crontab -e                          # edit current user crontab
crontab -l                          # list crontabs
crontab -u jsmith -e                # edit another user's crontab
sudo crontab -e                     # root crontab

# Cron syntax: MIN HOUR DOM MON DOW COMMAND
# *  *  *  *  * = every minute
# 0  2  *  *  * = 2:00 AM daily
# 0  2  *  *  0 = 2:00 AM Sundays
# 0  */6 *  *  * = every 6 hours
# */5 *  *  *  * = every 5 minutes
# 0  0  1  *  * = midnight, 1st of month

# Examples:
# 0 2 * * * /usr/bin/apt update     # apt update at 2 AM daily
# */5 * * * * /opt/check.sh         # every 5 minutes
# 0 0 * * 0 /opt/backup.sh         # weekly backup Sunday midnight
# @reboot /opt/startup.sh           # on every reboot
# @daily /opt/daily.sh              # once daily

# System cron directories:
ls /etc/cron.d/                     # cron files (custom jobs)
ls /etc/cron.daily/                 # scripts run daily
ls /etc/cron.weekly/                # scripts run weekly
ls /etc/cron.monthly/               # scripts run monthly
ls /etc/cron.hourly/                # scripts run hourly

# Check cron log
grep CRON /var/log/syslog | tail -20
journalctl -u cron --since today

# ── SYSTEMD TIMERS (preferred for system tasks) ──
# See references/services-systemd.md for full timer reference
systemctl list-timers               # list all active timers
systemctl list-timers --all         # including inactive
```

---

## BASH SCRIPTING ESSENTIALS

```bash
#!/bin/bash
# Shebang line — always first line

# ── VARIABLES ──
NAME="Ubuntu"
COUNT=42
RESULT=$(command)              # command substitution
RESULT=`command`               # alternative (older)
echo "Server: $NAME"
echo "Count: ${COUNT}"
readonly PI=3.14               # constant

# ── SPECIAL VARIABLES ──
$0   # script name
$1   # first argument
$@   # all arguments
$#   # number of arguments
$?   # exit code of last command (0=success)
$$   # current PID
$!   # PID of last background process

# ── CONDITIONALS ──
if [ "$1" = "start" ]; then
    echo "Starting..."
elif [ "$1" = "stop" ]; then
    echo "Stopping..."
else
    echo "Usage: $0 start|stop"
    exit 1
fi

# Test conditions:
# [ -f file ]   file exists and is regular file
# [ -d dir ]    directory exists
# [ -z "$var" ] string is empty
# [ -n "$var" ] string is not empty
# [ "$a" = "$b" ] strings equal
# [ $n -eq 5 ]  numbers equal
# [ $n -gt 5 ]  greater than
# [ $n -lt 5 ]  less than

# ── LOOPS ──
for i in {1..10}; do
    echo "Number: $i"
done

for file in /etc/*.conf; do
    echo "Config: $file"
done

while [ $COUNT -gt 0 ]; do
    echo "$COUNT"
    COUNT=$((COUNT-1))
done

# ── FUNCTIONS ──
check_service() {
    local SERVICE=$1
    if systemctl is-active --quiet "$SERVICE"; then
        echo "$SERVICE is running"
    else
        echo "$SERVICE is NOT running"
        return 1
    fi
}
check_service nginx

# ── ERROR HANDLING ──
set -e           # exit on error
set -u           # error on undefined variable
set -o pipefail  # catch pipe errors
set -euo pipefail  # all three (recommended)

# Trap for cleanup
trap 'echo "Error on line $LINENO"' ERR
trap 'rm -f /tmp/lockfile' EXIT

# ── USEFUL PATTERNS ──
# Check if root
if [ "$EUID" -ne 0 ]; then
    echo "Run as root"
    exit 1
fi

# Check if command exists
if ! command -v nginx &>/dev/null; then
    apt install -y nginx
fi

# Read file line by line
while IFS= read -r line; do
    echo "$line"
done < /etc/hosts

# Log with timestamp
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a /var/log/myscript.log; }
log "Script started"
```
