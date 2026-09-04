# WiFi Controller & FortiAP — FortiOS 7.4.11

> The screenshot shows FortiGate managing FortiAP devices.
> Models visible: FAP-223E and FAP231F running v7.4.2/v7.4.6.
> This reference covers the full wireless controller feature set.

---

## WiFi Controller Architecture

```
FortiGate (Wireless Controller)
    │
    ├── CAPWAP tunnel (UDP 5246 control, UDP 5247 data)
    │
    └── FortiAP
            ├── Radio 1 (2.4 GHz — R1)
            ├── Radio 2 (5 GHz — R2)
            └── Radio 3 (6 GHz — R3, on FAP-231F and newer)

Tunnel Mode: All client traffic tunneled to FortiGate (most secure)
Bridge Mode: Client traffic switched locally at AP level (better performance)
```

---

## Enable WiFi Controller

```bash
# GUI: System > Feature Visibility > WiFi Controller > Enable
config system settings
  set wireless-controller enable
end
```

---

## FortiAP Profiles (WTP Profiles)

### GUI: WiFi & Switch Controller > FortiAP Profiles

> **Note:** WTP profiles for FortiAP B, C, D-series and FortiAP-S are removed in 7.4.0+.
> Use platform-specific profiles (FAP-231F-default, FAP-223E-default, etc.)

```bash
config wireless-controller wtp-profile
  edit "FAP231F-Custom"
    set platform
      set type FAP231F
    end
    set comment "FAP231F Custom Profile"
    config radio 1
      set band 802.11ax-2G        # Wi-Fi 6 on 2.4GHz
      set channel 1 6 11          # non-overlapping channels
      set auto-power-level enable
      set auto-power-low 10       # min TX power (dBm)
      set auto-power-high 17      # max TX power (dBm)
      set protection-mode rtscts
    end
    config radio 2
      set band 802.11ax-5G        # Wi-Fi 6 on 5GHz
      set channel 36 40 44 48 149 153 157 161
      set auto-power-level enable
      set auto-power-low 10
      set auto-power-high 20
    end
    config radio 3
      set band 802.11ax-6G        # Wi-Fi 6E on 6GHz (FAP231F)
      set auto-power-level enable
    end
  next
end
```

---

## SSID Configuration (VAP — Virtual AP)

### GUI: WiFi & Switch Controller > SSIDs

```bash
# Tunnel mode SSID (All Tunnel Mode SSIDs — as shown in screenshot)
config wireless-controller vap
  edit "Corp-WiFi"
    set ssid "Corporate"
    set broadcast-ssid enable
    set security wpa2-only-enterprise    # 802.1X/RADIUS authentication
    set auth radius
    set radius-server "NPS-Server"
    set vdom "root"
    set vlanid 10
    set local-bridging disable           # tunnel mode
    set dhcp-lease-time 86400
    set intra-vap-privacy enable         # isolate clients
    set local-authentication disable
    set comment "Corporate Wi-Fi 802.1X"
  next

  edit "Guest-WiFi"
    set ssid "Guest-Internet"
    set broadcast-ssid enable
    set security wpa2-only-personal      # PSK
    set passphrase "GuestPass@2024"
    set vdom "root"
    set vlanid 20
    set local-bridging disable           # tunnel mode
    set captive-portal enable            # captive portal
    set portal-type disclaimer-email
    set dhcp-lease-time 3600             # 1 hour for guests
    set intra-vap-privacy enable
    set comment "Guest captive portal WiFi"
  next

  edit "IoT-WiFi"
    set ssid "IoT-Devices"
    set broadcast-ssid disable           # hidden SSID
    set security wpa2-only-personal
    set passphrase "IoTSecret@123"
    set vdom "root"
    set vlanid 30
    set local-bridging disable
    set intra-vap-privacy enable         # client isolation
  next
end
```

---

## FortiAP (WTP) Registration & Management

### GUI: WiFi & Switch Controller > Managed FortiAPs

```bash
# List all discovered/managed APs
config wireless-controller wtp
  show

# Manually approve/register an AP
config wireless-controller wtp
  edit "FP231F-SERIALNUMBER"
    set admin enable              # approve the AP
    set name "AP-Floor1-Room101"
    set wtp-profile "FAP231F-Custom"
    set location "Floor 1 - Room 101"
    config radio 1
      config vap-all override
        set vaps "Corp-WiFi" "Guest-WiFi"   # assign SSIDs to radio
      end
    end
    config radio 2
      config vap-all override
        set vaps "Corp-WiFi" "Guest-WiFi"
      end
    end
    config radio 3
      config vap-all override
        set vaps "Corp-WiFi"
      end
    end
  next
end
```

---

## AP Connection Methods

```bash
# CAPWAP discovery methods (in order):
# 1. DHCP Option 138 (controller IP)
# 2. DNS lookup: "fortiwifi.local"
# 3. Broadcast on local subnet
# 4. Manually configured AC_IPADDR on AP

# On FortiAP CLI — configure controller IP
cfg -a AC_IPADDR_1="192.168.10.1"     # FortiGate IP
cfg -a AC_IPADDR_2="192.168.10.2"     # Secondary controller (HA)
cfg -s                                  # save config
cfg -c                                  # view config

# Change AP IP (from DHCP to static)
cfg -a ADDR_MODE=STATIC
cfg -a AP_IPADDR="192.168.10.100"
cfg -a AP_NETMASK="255.255.255.0"
cfg -a IPGW="192.168.10.1"
cfg -s

# Reset AP to factory default
cfg -x
```

---

## FortiAP CAPWAP Firewall Policy

```bash
# Allow FortiAP to reach FortiGate (if AP is on different VLAN/subnet)
config firewall policy
  edit 500
    set name "FortiAP-CAPWAP"
    set srcintf "port3"           # interface where APs connect
    set dstintf "any"
    set srcaddr "FortiAP-Subnet"  # AP management subnet
    set dstaddr "FortiGate-IP"
    set action accept
    set schedule "always"
    set service "CAPWAP"          # UDP/5246, UDP/5247
  next
end
```

---

## Rogue AP Detection

```bash
# Enable rogue AP detection
config wireless-controller global
  set rogue-scan enable
end

# View rogue APs (GUI: WiFi > Rogue AP Monitor)
diag wireless-controller wlac -c ap-rogue

# Contain rogue AP (deauth clients)
# GUI: WiFi > Rogue AP Monitor > select AP > Suppress
```

---

## Radio Resource Management

```bash
# Spectrum analysis
exec wireless-controller spectral-scan <wtp-id> <radio-id> on <duration-sec> <channel> <report-interval>

# View spectrum analysis results
diag wireless-controller wlac -c rfsa <wtp-id> <radio-id> <channel>
get wireless-controller spectral-info <wtp-id> <radio-id>
```

---

## WiFi Diagnostics

```bash
# Restart wireless controller daemon
exec wireless-controller restart-acd

# Restart all managed FortiAPs
exec wireless-controller reset-wtp

# Restart specific FortiAP
exec wireless-controller reset-wtp <wtp-id>

# WLAN client list (GUI: WiFi > Clients)
diag wireless-controller wlac -c sta-all

# AP status info
diag wireless-controller wlac -c wtp-all

# SSID station count
diag wireless-controller wlac -c vap-all

# Debug CAPWAP
diag debug appl cw_acd -1
diag debug enable

# Check connected APs and radio info (CLI)
get wireless-controller wtp
```

---

## SSID Authentication Methods Summary

| Method | Security | Config key |
|---|---|---|
| Open | None (captive portal) | `set security open` |
| WPA2-Personal | PSK | `set security wpa2-only-personal` |
| WPA3-Personal | SAE | `set security wpa3-sae` |
| WPA2-Enterprise | 802.1X RADIUS | `set security wpa2-only-enterprise` |
| WPA3-Enterprise | 802.1X + SAE | `set security wpa3-enterprise` |
| OWE | Opportunistic wireless encryption | `set security owe` |

---

## WiFi Best Practices (7.4.11)

1. Use **WPA3** on new deployments where clients support it.
2. Enable **client isolation** (`intra-vap-privacy enable`) for Guest SSIDs.
3. Use **separate VLANs** for Corporate / Guest / IoT.
4. Enable **802.11r (Fast Roaming)** for VoIP/mobility environments.
5. Use **auto-power-level** to avoid co-channel interference.
6. Monitor via **WiFi Dashboard** in FortiGate GUI for real-time client/AP visibility.
7. Assign dedicated **FortiAP profiles** per AP model (FAP-231F, FAP-223E, etc.).
8. For large deployments, use **FortiManager** to push wireless config centrally.
