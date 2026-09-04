# 13 — Firmware Upgrade & Backup / Restore
## Fujitsu PSWITCH 2048P (ET-7648BFRA-FOS) | FW 1.3.x

---

## FIRMWARE SLOTS

The switch maintains **two firmware slots** (active and backup).
```
show version
# Output shows:
#   Active firmware: 1.3.68
#   Backup firmware: 1.3.40
```

---

## FIRMWARE UPGRADE — TFTP

```
# Step 1: Verify connectivity to TFTP server
ping 192.168.1.10

# Step 2: Upload firmware
copy tftp://192.168.1.10/pswitch2048p-1.3.68.bin system:image

# Step 3: Set which slot to boot from (if needed)
bootselect image1      ← or image2

# Step 4: Reboot
reload

show version           ← confirm after reboot
```

---

## FIRMWARE UPGRADE — USB

```
# Insert USB drive with firmware file
dir usb

# Copy from USB
copy usb://pswitch2048p-1.3.68.bin system:image

# Eject USB before reboot
eject usb

reload
show version
```

---

## BACKUP / RESTORE CONFIGURATION

### Save Running Config
```
# To startup-config (persistent across reboot)
copy running-config startup-config

# To TFTP
copy running-config tftp://192.168.1.10/switch-backup.cfg

# To USB
copy running-config usb://switch-backup.cfg

# To backup-config slot (on-device third config slot)
copy running-config backup-config
```

### Restore Configuration
```
# From TFTP to startup
copy tftp://192.168.1.10/switch-backup.cfg startup-config

# From USB to startup
copy usb://switch-backup.cfg startup-config

# From backup-config slot to startup
copy backup-config startup-config

# Apply running without reboot (merge)
copy tftp://192.168.1.10/switch-backup.cfg running-config
```

### View Config Differences
```
show running-config
show startup-config
show backup-config
```

---

## FACTORY RESET

```
erase factory-defaults
reboot
```
> **Warning:** This deletes ALL configuration including IP settings.

---

## DIAGNOSTIC INFORMATION COLLECTION

```
show tech-support
# Collects: version, config, interfaces, logs, routing, spanning-tree, etc.

# Save to TFTP
copy debug tftp://192.168.1.10/techsupport.log
```

---

## POST (Power-On Self-Test)

```
# Enable extended POST
(Config)# post extended

# Disable POST (faster boot)
(Config)# no post

show post
```

---

## UPGRADE PATH NOTES (FW 1.3.x)

| From Version | To 1.3.68 | Notes |
|-------------|-----------|-------|
| 1.2.x | Direct | Supported |
| 1.3.x | Direct | Supported — same major train |
| 1.0.x / 1.1.x | Step-wise recommended | Upgrade to 1.2.x first |

---

## FUJITSU SUPPORT PORTAL

Firmware downloads and release notes:
```
https://support.ts.fujitsu.com
Product: Networking → PSWITCH 2048P
```

Firmware filename pattern:
```
pswitch2048p_<version>.bin
```
