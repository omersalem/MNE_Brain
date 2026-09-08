# FortiGate to FortiAnalyzer Registration & Log Shipping Guide

This guide details the complete end-to-end workflow to connect, register, authorize, and verify any FortiGate firewall (HQ or Branch) with the centralized **FortiAnalyzer 7.4.10 (172.23.71.206)**.

---

## Architecture of FortiGate ➔ FortiAnalyzer Connection

FortiGate communicates with FortiAnalyzer over **OFTP (Open Fabric Telemetry Protocol)** using:
- **Port 514 (TCP/UDP):** Standard log forwarding.
- **Port 8514 (TCP over TLS):** Encrypted, reliable log transport (Recommended).
- **Handshake Flow:**
  1. FortiGate initiates connection to FortiAnalyzer IP (`172.23.71.206`).
  2. FortiAnalyzer receives the probe and marks the FortiGate as **Unregistered**.
  3. Security Administrator authorizes the FortiGate in FortiAnalyzer (assigning it to an ADOM).
  4. Encrypted session is established; logs flow in real-time.

---

## 1. Step 1: Configure FortiGate to Send Logs to FortiAnalyzer

### Option A: Via FortiGate Web GUI
1. Log in to the target FortiGate web GUI (e.g. `https://172.23.70.4` for HQ).
2. Navigate to **Security Fabric > Fabric Connectors** (or **Log & Report > Log Settings**).
3. Locate **FortiAnalyzer**:
   - Toggle **Status** to **Enable**.
   - **IP Address:** Enter `172.23.71.206`.
   - **Upload Option:** Select **Realtime** (or **Every Minute / Hourly**).
   - **Encrypt Log Transmission:** Select **High-Medium** or **High**.
4. Click **Apply**.
5. The FortiGate will display **Connection Status: Pending Authorization** (or "Waiting for authorization from FortiAnalyzer").

### Option B: Via FortiGate CLI (Recommended for Automation)
SSH into the FortiGate and run:
```bash
config log fortianalyzer setting
    set status enable
    set server 172.23.71.206
    set upload-option realtime
    set reliable enable
    set enc-algorithm high-medium
    set ssl-min-proto-version default
end
```

---

## 2. Step 2: Authorize the FortiGate in FortiAnalyzer

### Option A: Via FortiAnalyzer Web GUI
1. Log in to FortiAnalyzer: `https://172.23.71.206/`.
2. Go to **Device Manager > Device & Groups**.
3. Look at the top banner or left navigation tree for **Unauthorized Devices**.
4. Click on **Unauthorized Devices**:
   - Select the checkbox next to the pending FortiGate.
   - Review detected IP address, serial number, and firmware version.
   - Click the **Authorize** button in the toolbar.
   - Set **ADOM**: Select `root`.
   - Set **Device Name**: Assign a clear canonical name (e.g. `FW-MNE-Jericho`).
5. Click **OK**. The device moves to **Managed Devices** and displays a green checkmark.

### Option B: Via FortiAnalyzer CLI
SSH into FortiAnalyzer (`172.23.71.206`) as `admin`:
```bash
# 1. Verify the device is detected in unregistered state:
diagnose dvm device list

# 2. Authorize and promote the device:
execute device promote <serial-number-or-device-name>
```

---

## 3. Step 3: Verification & Health Check

### 3.1 Verify Connection on the FortiGate
Run this diagnostic command on the FortiGate CLI:
```bash
diagnose log fortianalyzer status
```

**Expected Healthy Output:**
```
Server: 172.23.71.206
Status: Connected
SSL/TLS: Enabled (High-Medium)
Reliable: Enabled
Queue size: 0 (no backlog)
```

### 3.2 Send a Test Log Message from FortiGate
To generate an immediate test log to confirm reception:
```bash
diagnose log fortianalyzer test
```

### 3.3 Confirm Logs in FortiAnalyzer
1. On FortiAnalyzer GUI, go to **Log View > Traffic** or **Log View > Event**.
2. Filter by Device: Select the newly added FortiGate.
3. Verify new log events are streaming with current timestamps.

---

## 4. Troubleshooting Common Connection Issues

| Symptom | Probable Cause | Corrective Action |
|---|---|---|
| **Status: Waiting for Auth** | Device not yet authorized on FAZ | Go to FAZ **Device Manager > Unauthorized Devices** and click **Authorize**. |
| **Status: Connection Failed** | Port 514 / 8514 blocked or routing missing | Run `execute ping 172.23.71.206` from FortiGate. Verify firewall policy allows traffic to FAZ. |
| **SSL/TLS handshake error** | Mismatched SSL protocols / ciphers | On FortiGate, ensure `set ssl-min-proto-version default`. Check date/time sync between FGT and FAZ. |
| **Logs queued / backlog growing** | ADOM disk quota exceeded | Expand ADOM quota on FortiAnalyzer (`System Settings > Storage Info`). |
