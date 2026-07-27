---
id: "MNE-CONN-FLOOR-SWITCHES"
title: "conn-sw-floor-switches"
type: "connection_profile"
status: "active"
device_type: "cisco_access_switch"
site: "HQ"
owner: "Network-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/cisco
---

# Connection Profile Matrix: Campus Floor Access Switches

Context: [[master-dashboard]] | Related Asset: [[sw-cisco-access-01]]

## 🔐 Common Credentials & Parameters
- **Access Level:** Read-Only (User EXEC)
- **Port:** 22 (SSH)
- **Username:** `admin`
- **Password:** `LOADED_FROM_ENV`
- **Protocol:** SSH (`Netmiko`)

## 🏢 Switch Fleet IP Allocations
| Floor | Hostname | Management IP | Status |
| :--- | :--- | :--- | :--- |
| **Khadamat / Service** | `Khadamat` | `172.23.70.219` | Active |
| **Basement (B1)** | `F_-1_acc_Sw1` | `172.23.70.220` | Active |
| **Ground Floor** | `F0_acc_Sw1` | `172.23.70.221` | Active |
| **Floor 1** | `F1_acc_Main` | `172.23.70.222` | Active |
| **Floor 2** | `f2_acc_sw1` | `172.23.70.223` | Active |
| **Floor 3** | `f3_acc_sw1` | `172.23.70.224` | Active |
| **Floor 4** | `F4_acc_sw1` | `172.23.70.225` | Active |
| **Floor 5** | `Floor_5_main` | `172.23.70.226` | Active |
| **Floor 6** | `F6_acc_Sw1` | `172.23.70.227` | Active |

## 🔗 Related Wiki Pages
- Primary Asset: [[sw-cisco-access-01]]
