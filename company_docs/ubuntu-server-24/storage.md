# Storage & LVM — Ubuntu Server 24.04
## Disks, Partitions, Filesystems, LVM, Mount, RAID

---

## DISK INFORMATION

```bash
# ── LIST DISKS & PARTITIONS ──
lsblk                               # block devices tree
lsblk -f                            # with filesystem + UUID
lsblk -o NAME,SIZE,FSTYPE,UUID,MOUNTPOINT  # custom columns
fdisk -l                            # disk details + partition table
fdisk -l /dev/sda                   # specific disk
parted -l                           # parted disk list
blkid                               # all devices + UUID + type
blkid /dev/sda1                     # specific partition

# ── DISK USAGE ──
df -h                               # filesystem usage (human-readable)
df -hT                              # with filesystem type
df -h /var                          # specific mount point
du -sh /var/log/                    # directory size
du -sh /var/log/* | sort -h         # sorted
du -h --max-depth=1 /               # top-level dirs

# ── DISK PERFORMANCE ──
iostat -x 1 5                       # extended stats, every 1s, 5 times
iostat -d -h                        # disk stats, human-readable
iotop                               # live I/O monitor (apt install iotop)
iotop -o                            # only processes with active I/O
hdparm -Tt /dev/sda                 # disk speed test
fio --name=test --rw=randread --bs=4k --size=1G  # advanced I/O test
```

---

## PARTITIONING

### fdisk (MBR/GPT)
```bash
sudo fdisk /dev/sdb                 # interactive partitioning

# fdisk commands:
# m — help (menu)
# n — new partition
# p — primary, e — extended
# d — delete partition
# l — list partition types
# t — change partition type
# w — write and exit
# q — quit without saving
# p — print partition table
# g — create new GPT table
# o — create new MBR table

# fdisk one-liner to create single partition:
echo -e "n\np\n1\n\n\nw" | sudo fdisk /dev/sdb
```

### parted (preferred for GPT/large disks)
```bash
sudo parted /dev/sdb                # interactive

# parted commands:
sudo parted /dev/sdb mklabel gpt    # create GPT table
sudo parted /dev/sdb mklabel msdos  # create MBR table
sudo parted /dev/sdb mkpart primary ext4 0% 100%   # full disk
sudo parted /dev/sdb mkpart primary ext4 0% 50%    # first half
sudo parted /dev/sdb mkpart primary ext4 50% 100%  # second half
sudo parted /dev/sdb print          # show partition table
sudo parted /dev/sdb rm 1           # remove partition 1

# Non-interactive:
sudo parted -s /dev/sdb mklabel gpt
sudo parted -s /dev/sdb mkpart primary ext4 0% 100%
```

---

## FILESYSTEMS

```bash
# ── CREATE FILESYSTEMS ──
sudo mkfs.ext4 /dev/sdb1            # create ext4 filesystem
sudo mkfs.ext4 -L "MyData" /dev/sdb1  # with label
sudo mkfs.xfs /dev/sdb1             # create XFS filesystem
sudo mkfs.xfs -L "MyData" /dev/sdb1
sudo mkfs.vfat /dev/sdb1            # create FAT32
sudo mkswap /dev/sdb2               # create swap

# ── MOUNT ──
sudo mount /dev/sdb1 /mnt/data      # basic mount
sudo mount -t ext4 /dev/sdb1 /mnt/data  # explicit type
sudo mount -o ro /dev/sdb1 /mnt/    # read-only
sudo mount -o remount,rw /mnt/      # remount as read-write
sudo mount -a                       # mount all from /etc/fstab
sudo umount /mnt/data               # unmount
sudo umount -l /mnt/data            # lazy unmount (when busy)

# ── /etc/fstab (PERSISTENT MOUNTS) ──
# Format: device  mountpoint  fstype  options  dump  pass
# Get UUID: blkid /dev/sdb1
UUID=abc-123  /mnt/data  ext4   defaults   0  2
UUID=def-456  /mnt/nas   xfs    defaults,noatime  0  2
UUID=ghi-789  none       swap   sw         0  0
# tmpfs (RAM disk):
tmpfs  /tmp  tmpfs  defaults,noatime,size=2G  0  0
# NFS:
192.168.1.10:/share  /mnt/nfs  nfs  defaults,_netdev  0  0

# Test fstab:
sudo mount -a                       # mount all fstab entries
sudo findmnt --verify               # verify fstab

# ── FILESYSTEM CHECKS ──
sudo fsck /dev/sdb1                 # check filesystem (must be unmounted)
sudo fsck -n /dev/sdb1              # check only (no repair)
sudo e2fsck -f /dev/sdb1            # ext4 force check
sudo xfs_repair /dev/sdb1           # XFS repair

# ── FILESYSTEM INFO ──
sudo tune2fs -l /dev/sdb1           # ext4 filesystem info
sudo xfs_info /dev/sdb1             # XFS filesystem info
sudo dumpe2fs /dev/sdb1             # detailed ext4 info

# ── RESIZE FILESYSTEMS ──
sudo resize2fs /dev/sdb1            # grow ext4 to partition size (online)
sudo resize2fs /dev/sdb1 10G        # resize to specific size
sudo xfs_growfs /mnt/data           # grow XFS (must be mounted)
```

---

## LVM — LOGICAL VOLUME MANAGEMENT

### LVM Concepts
```
Physical Volume (PV): /dev/sdb, /dev/sdc, /dev/sdb1
  └── Volume Group (VG): ubuntu-vg, data-vg
        └── Logical Volume (LV): /dev/ubuntu-vg/root, /dev/ubuntu-vg/data
              └── Filesystem: ext4, xfs
```

### Physical Volumes (PV)
```bash
# ── VIEW ──
sudo pvs                            # summary
sudo pvdisplay                      # detailed
sudo pvdisplay /dev/sdb             # specific PV

# ── CREATE ──
sudo pvcreate /dev/sdb              # whole disk as PV
sudo pvcreate /dev/sdb1 /dev/sdc1  # multiple partitions

# ── REMOVE ──
sudo pvremove /dev/sdb              # remove PV (must remove from VG first)

# ── MOVE (migrate data off a disk) ──
sudo pvmove /dev/sdb                # move all data off /dev/sdb
sudo pvmove /dev/sdb /dev/sdc       # move specifically to /dev/sdc
```

### Volume Groups (VG)
```bash
# ── VIEW ──
sudo vgs                            # summary
sudo vgdisplay                      # detailed
sudo vgdisplay ubuntu-vg            # specific VG

# ── CREATE ──
sudo vgcreate ubuntu-vg /dev/sdb    # create VG from PV
sudo vgcreate data-vg /dev/sdb /dev/sdc  # from multiple PVs

# ── EXTEND ──
sudo vgextend ubuntu-vg /dev/sdc    # add new PV to VG

# ── REDUCE ──
sudo vgreduce ubuntu-vg /dev/sdb    # remove PV from VG (after pvmove)

# ── RENAME / REMOVE ──
sudo vgrename ubuntu-vg new-vg      # rename VG
sudo vgremove ubuntu-vg             # remove VG (must remove LVs first)

# ── EXPORT / IMPORT (move to another system) ──
sudo vgexport ubuntu-vg             # export VG
sudo vgimport ubuntu-vg             # import VG
```

### Logical Volumes (LV)
```bash
# ── VIEW ──
sudo lvs                            # summary
sudo lvdisplay                      # detailed
sudo lvdisplay /dev/ubuntu-vg/root  # specific LV

# ── CREATE ──
sudo lvcreate -L 20G -n root ubuntu-vg     # fixed size (20GB)
sudo lvcreate -l 100%FREE -n data ubuntu-vg  # use all free space
sudo lvcreate -l 50%FREE -n data ubuntu-vg   # use 50% of free space
sudo lvcreate -l +50G -n data ubuntu-vg      # add 50GB

# After creating LV: create filesystem and mount
sudo mkfs.ext4 /dev/ubuntu-vg/data
sudo mkdir -p /mnt/data
sudo mount /dev/ubuntu-vg/data /mnt/data

# ── EXTEND (grow LV) ──
sudo lvextend -L +10G /dev/ubuntu-vg/data       # add 10GB
sudo lvextend -L 50G /dev/ubuntu-vg/data        # set to 50GB total
sudo lvextend -l +100%FREE /dev/ubuntu-vg/data  # use all free space

# After extending LV, resize filesystem:
sudo resize2fs /dev/ubuntu-vg/data              # ext4 (online)
sudo xfs_growfs /mnt/data                       # xfs (must be mounted)

# One-command extend + resize:
sudo lvextend -r -L +10G /dev/ubuntu-vg/data    # -r = resize filesystem too

# ── REDUCE (shrink LV — RISKY, always backup first!) ──
# ext4 only (XFS cannot shrink):
sudo umount /mnt/data                           # unmount first
sudo e2fsck -f /dev/ubuntu-vg/data             # check filesystem
sudo resize2fs /dev/ubuntu-vg/data 30G         # shrink filesystem to 30GB
sudo lvreduce -L 30G /dev/ubuntu-vg/data       # then shrink LV

# ── RENAME ──
sudo lvrename ubuntu-vg oldname newname

# ── REMOVE ──
sudo umount /mnt/data                           # unmount first
sudo lvremove /dev/ubuntu-vg/data              # remove LV

# ── SNAPSHOT ──
# Create snapshot (for backup or testing)
sudo lvcreate -L 5G -s -n data-snap /dev/ubuntu-vg/data
# Mount snapshot:
sudo mount -o ro /dev/ubuntu-vg/data-snap /mnt/snap
# Remove snapshot:
sudo lvremove /dev/ubuntu-vg/data-snap
```

---

## SWAP MANAGEMENT

```bash
# ── VIEW ──
swapon --show                       # active swap
free -h                             # memory + swap usage
cat /proc/swaps                     # swap devices

# ── FILE-BASED SWAP ──
sudo fallocate -l 4G /swapfile      # create 4GB swap file
sudo chmod 600 /swapfile            # secure permissions
sudo mkswap /swapfile               # format as swap
sudo swapon /swapfile               # enable

# Make permanent (/etc/fstab):
echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab

# ── PARTITION-BASED SWAP ──
sudo mkswap /dev/sdb2               # format partition as swap
sudo swapon /dev/sdb2               # enable

# ── SWAPPINESS ──
cat /proc/sys/vm/swappiness         # current value (default: 60)
sudo sysctl vm.swappiness=10        # set to 10 (lower = use RAM more)
# Permanent:
echo "vm.swappiness=10" | sudo tee /etc/sysctl.d/99-swappiness.conf
sudo sysctl --system

# ── DISABLE SWAP ──
sudo swapoff /swapfile              # disable swap
sudo swapoff -a                     # disable all swap
```

---

## MONITORING STORAGE

```bash
# Real-time I/O
iostat -x 1                         # extended I/O stats every 1s
iotop -o                            # processes with active I/O
dstat -d                            # disk stats (apt install dstat)

# Disk health (SMART)
sudo apt install smartmontools
sudo smartctl -a /dev/sda           # full disk health report
sudo smartctl -H /dev/sda           # health status only
sudo smartctl -t short /dev/sda     # run short self-test
sudo smartctl -t long /dev/sda      # run long self-test (hours)

# Find large files eating disk space
find / -size +1G -type f 2>/dev/null | sort -k5 -n
du -sh /var/* | sort -rh | head -10
ncdu /                              # interactive (apt install ncdu)

# Inode usage (when disk shows full but df shows space)
df -i                               # inode usage per filesystem
find /tmp -type f | wc -l           # count files in /tmp
```
