# FortiAnalyzer 7.4.10 — Exact Web GUI Configuration Guide

This guide is **100% verified and matched against the live FortiAnalyzer 7.4.10 (build 2778)** appliance running on `https://172.23.71.206/`.

---

## 1. Overall Interface Architecture

The interface consists of three distinct regions:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [Logo] FAZVM64 [≡]                                          [>_] [?] [🔔 2] [👤 admin ▾]│
├───────────────────┬────────────────────────────────────────────────────────────────────┤
│ > Dashboards      │ Main Content Workspace                                             │
│   Device Manager  │                                                                    │
│ > FortiView       │ (Displays Dashboards, Device Manager, Log View, or System Settings)│
│ > Log View        │                                                                    │
│ > Fabric View     │                                                                    │
│ > Incidents & Ev. │                                                                    │
│ > Reports         │                                                                    │
│ v System Settings │                                                                    │
│   - ADOMs         │                                                                    │
│   - Administrators│                                                                    │
│   - Admin Profiles│                                                                    │
│   - Remote Auth...│                                                                    │
│   - Fabric Mgmt   │                                                                    │
│   - SAML SSO      │                                                                    │
│   - Settings      │                                                                    │
│   - HA            │                                                                    │
│   - Network       │                                                                    │
│   - Event Logs    │                                                                    │
│   - Certificates  │                                                                    │
│   - Advanced      │                                                                    │
│                   │                                                                    │
│ [FORTINET Logo]   │                                                                    │
└───────────────────┴────────────────────────────────────────────────────────────────────┘
```

---

## 2. Top Header Controls

- **Left:** Fortinet circle logo + Hostname `FAZVM64` + `☰` hamburger icon (collapses/expands left sidebar).
- **Right:**
  - **`>_` (CLI Console Drawer):** Opens an interactive CLI console drawer at the bottom of the screen.
  - **`?` (Help):** Links directly to Fortinet Document Library and product support.
  - **`🔔 2` (Notifications):** Unread system alerts, backup notices, and admin messages.
  - **`👤 admin ▾` (User Profile Menu):**
    - `Change Password`
    - `Preferences`
    - `Configuration > Backup` (Download full system `.dat` backup)
    - `Configuration > Restore`
    - `System > Reboot` / `Shutdown`
    - `Log Out`

---

## 3. Left Sidebar Navigation (8 Main Sections)

1. **`Dashboards`** (expandable `>`): System Information widget (`FAZVM64`, SN `FAZVMSTM24000372`, `v7.4.10 build2778 Mature`), Unit Operation / System Resources (CPU/Memory/Disk), and Log Rate monitors.
2. **`Device Manager`**: Central view of all 14 managed firewalls (`FG-MNE`, `FW-MNE-Bethlahem`, `FW-MNE-Hebron`, etc.) and the **Unauthorized Devices** tab.
3. **`FortiView`** (expandable `>`): SOC visual analytics: Top Threats, Top Sources/Destinations, Top Applications, VPN Monitor.
4. **`Log View`** (expandable `>`): Searchable logs: Traffic, Security (Antivirus, Web Filter, IPS, App Control), and System Event logs.
5. **`Fabric View`** (expandable `>`): Physical/Logical Security Fabric maps and asset tracking.
6. **`Incidents & Events`** (expandable `>`): Incident cases, Event Monitor, and rule-based Event Handlers.
7. **`Reports`** (expandable `>`): Pre-built report templates, historical generated reports, and schedules.
8. **`System Settings`** (expanded submenu):
   - **`ADOMs`**
   - **`Administrators`**
   - **`Admin Profiles`**
   - **`Remote Authentication ...`**
   - **`Fabric Management`**
   - **`SAML SSO`**
   - **`Settings`**
   - **`HA`**
   - **`Network`**
   - **`Event Logs`**
   - **`Certificates`**
   - **`Advanced`**

---

## 4. Step-by-Step Task Guides

---

### Task 1: Expanding Storage Quota in `System Settings > ADOMs`

> [!CAUTION]
> **Storage Quota Saturation Warning:**
> Live audit confirmed the SQL Analytics Database is at **91.4% saturation** (`40.3 GB` used out of `44.1 GB` quota), while the physical disk has **378.1 GB unallocated free space**.
> FortiAnalyzer **automatically purges older logs** whenever the allocated quota is reached, regardless of how many retention days are configured!

#### Step 1: Open the ADOM Table
1. In the left navigation sidebar, click **`System Settings > ADOMs`**.
2. On the main page, you will see the ADOM table:
   - **Toolbar:** `[ Edit ]` | `[ Delete ]` | `[ Enter ADOM ]` | `[ More ▾ ]` | `[ Full Screen ]`
   - **Group:** `[-] Security Fabric (1)`
   - **Row:** `[x] root` | ADOM Type: `Fabric` | **Allocated Storage: `63 GB`** | Devices: `14 Devices`

#### Step 2: Open the Edit ADOM Drawer
1. Select the **`root`** row and click the **`[ Edit ]`** button in the toolbar (or double-click the `root` row).
2. The **`Edit ADOM - root`** modal drawer opens on the right side of the screen.

#### Step 3: Understanding the Modal Layout & The "Nested Scroll Trap"

```
┌────────────────────────────────────────────────────────────┐
│ Edit ADOM - root                                       [x] │
├────────────────────────────────────────────────────────────┤
│ Name         root                                          │
│ Type         Fabric                                        │
│ Description  [                                      0/128] │
│                                                            │
│ Devices      [ + Select Device ]  [ Search... 🔍 ] [ ⚙ ]   │
│              ┌───────────────────────────────────────────┐ │
│              │ [ ] Name           IP Address  Platform   │ │
│              │ [ ] FG-GoldR       172.27.13.54  FG-81F  ▲│ │
│              │ [ ] FG-Jenin       172.27.13.26  FG-71G  █│ │  ◄── Inner Table Scrollbar
│              │ [ ] FG-Jericho     172.27.13.38  FG-60F  █│ │      (Scrolls firewalls only!)
│              │ [ ] FG MNE         213.6.17.30   FG-401F █│ │
│              │ ... (14 firewalls total)                 ▼│ │
│              └────────────────────────────────── 0% 14 ──┘ │
├────────────────────────────────────────────────────────────┤ ◄── (Pushed below fold in normal viewports)
│ ⚠️ SCROLL DOWN HERE: Hover over left column or drag outer scrollbar!
│                                                            │
│ Data Policy                                                │
│   Keep Logs for Analytics: [ 60 ] [ Days ▾ ]               │
│   Keep Logs for Archive:   [ 100] [ Days ▾ ]               │
│                                                            │
│ Disk Utilization                                           │
│   Allocated:               [ 63 ] [ GB ▾ ]                 │  ◄── Change 63 to 300 GB here!
│   Maximum Available:       378.1 GB                        │
│   Analytics: Archive:      [ 70% ] [ 30% ] [ ] Modify      │
│   Alert and Delete When Usage Reaches: [ 90% ▾ ]           │
│   *If analytic or archive log usages exceed the configured │
│    disk quota before retention expires, logs are deleted.  │
├────────────────────────────────────────────────────────────┤
│                                     [  OK  ]   [ Cancel ]  │
└────────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> **The Nested Scroll Trap:**
> Notice that the **Devices** sub-table contains 14 firewalls and has its own inner vertical scrollbar (`0% 14`).
> If you roll your mouse wheel while hovering directly over the firewall list, **only the firewall table will scroll**.
> To scroll down the entire modal to reach **`Data Policy`** and **`Disk Utilization`**:
> 1. Move your mouse cursor away from the table to the **left column** (over the label words `Description` or `Devices`), then roll the mouse wheel down; OR
> 2. Click and drag the **outer vertical scrollbar** located on the far right edge of the modal window.

#### Step 4: Configure Retention and Quota
1. **Under `Data Policy`:**
   - **`Keep Logs for Analytics`**: Change `60` to **`90`** or **`180`** Days.
   - **`Keep Logs for Archive`**: Change `100` to **`180`** or **`365`** Days.
2. **Under `Disk Utilization`:**
   - **`Allocated`**: Change `63` to **`300`** (and keep the unit dropdown on `GB`).
   - Notice **`Maximum Available`** indicates `378.1 GB` of unallocated space.
   - **`Analytics: Archive`**: Leave default (`70%` / `30%`) or check `[ ] Modify` if you want a custom ratio.
   - **`Alert and Delete When Usage Reaches`**: Keep at `90%`.
3. Click the blue **`[ OK ]`** button at the bottom of the modal.
4. The main table column **`Allocated Storage`** will update immediately from `63 GB` to `300 GB`.

---

### Task 2: System Settings > Settings (Admin & View Settings)

*(Matches your live configuration screen in `System Settings > Settings`)*

1. In the left sidebar, click **`System Settings > Settings`**.
2. **`Administration Settings` Pane:**
   - **`HTTP Port`**: `80` (numeric input spinner).
   - **`Redirects to HTTPS`**: Toggle switch directly below HTTP Port (ensure it is **enabled in orange**).
   - **`HTTPS Port`**: `443`.
   - **`HTTPS & Web Service Certificate`**: `✔ server.crt` (dropdown).
   - **`Idle Timeout`**: `900` Seconds (range 60–28800).
   - **`Idle Timeout (API)`**: `900` Seconds (range 1–28800).
   - **`Idle Timeout (GUI)`**: `900` Seconds (range 60–28800).
3. **`View Settings` Pane:**
   - **`Language`**: `Auto Detect` dropdown.
   - **`High Contrast Theme`**: Toggle switch (off).
   - **`Other Themes`**: Grid of 27 theme cards (`Mariner`, `Jade`, `Neutrino`, `Dark Matter`, `Spring`, `Summer`, `Autumn` [selected with white checkmark in orange circle], `Winter`, `Circuit Board`, etc.).
4. Click the golden/orange **`Apply`** button at the bottom center.

---

### Task 3: Authorizing Firewalls in `Device Manager`

1. In the left navigation sidebar, click **`Device Manager`**.
2. In the **Device Tree** on the left side of the workspace, review the folders:
   - **`All Logging Devices`** (or `Logging FortiGate`): Contains all currently authorized firewalls (14 devices).
   - **`Unauthorized Devices`**: Displays newly discovered firewalls sending logs to `172.23.71.206` that require authorization.
3. Click **`Unauthorized Devices`** to view the pending firewalls.
4. Select the checkbox next to the firewall you wish to register.
5. In the top toolbar, click **`Authorize`**:
   - Verify detected IP address, serial number, and firmware version.
   - Target ADOM: select `root`.
   - Set custom display name (e.g. `FW-MNE-Jericho`).
6. Click **`OK`**. The firewall transitions to **`All Logging Devices`** with a green operational status indicator.

---

### Task 4: System Settings > Network (Interfaces, Routing & DNS)

1. In the left navigation sidebar, click **`System Settings > Network`**.
2. **`Interfaces` Tab:**
   - Shows physical management interfaces (`port1`–`port4`).
   - Double-click **`port1`**:
     - IP / Netmask: `172.23.71.206 / 255.255.255.0` (`/24`).
     - Administrative Access: Check `HTTPS`, `SSH`, and `Ping`. (Disable `HTTP` if redirect is active).
     - Status: `Up`.
3. **`Routing` Tab:**
   - Verify default static route:
     - Destination: `0.0.0.0 / 0.0.0.0`
     - Gateway: `172.23.71.4`
     - Interface: `port1`
4. **`DNS` Tab:**
   - **Primary DNS:** `172.23.71.27` (`MNE-DC1.mne.gov.ps`).
   - **Secondary DNS:** `172.23.71.28` (`MNE-DC2.mne.gov.ps`).
5. Click **`Apply`**.

---

### Task 5: Downloading Configuration Backup

1. In the top-right header, click the **`👤 admin ▾`** profile icon.
2. Select **`Configuration > Backup`**.
3. In the dialog:
   - **Scope:** Select `Complete System Configuration`.
   - **Encryption:** (Optional) Check `Encrypt Backup` and enter a strong passphrase.
4. Click **`OK`**. The encrypted `.dat` configuration file will download to your local machine.

---

### Task 6: Monitoring Appliance Health in `Dashboards`

1. In the left navigation sidebar, click **`Dashboards`**.
2. **`System Information` Widget:**
   - **Host Name:** `FAZVM64` (click the edit pencil icon to rename).
   - **Serial Number:** `FAZVMSTM24000372` (click the copy icon to copy to clipboard).
   - **Platform Type:** `FAZVM64`.
   - **HA Status:** `Standalone`.
   - **System Time:** `Mon Sep 07 10:48:26 2026 IDT` (edit icon to change NTP/timezone).
   - **Firmware Version:** `v7.4.10 build2778 (Mature)` (upload icon to upgrade firmware image).
   - **System Configuration:** `Last Backup: Wed Feb 25 12:27:18 2026` (direct backup and restore icons).
   - **Current Administrators:** `admin / 1 in total` (view details icon).
   - **Up Time:** Displays cumulative operational uptime.
3. **`Unit Operation` Widget:**
   - Real-time gauges for CPU utilization, Memory usage, and Hard Disk allocation.
