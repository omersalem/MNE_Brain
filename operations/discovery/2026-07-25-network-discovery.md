# Automated Discovery Report: NETWORK

## 📊 Execution Summary
- **Execution Timestamp:** 2026-07-25T18:28:48.466531
- **Target Domain Task:** `network`
- **Execution Duration:** 0.12 Seconds
- **Runner Host Machine:** `172.23.50.62` (Windows Self-Hosted Runner)
- **Execution Status:** COMPLETED (Read-Only Telemetry)

## 🖥️ Devices & Connection Status
- **Devices Checked (5):**
  - FG-MNE-HQ (FortiGate CLI / REST API)
  - sw-cisco-core-01 (Cisco IOS-XE SSH)
  - 172.23.70.77 (Cisco FMC REST API)
  - 172.23.70.78 (Cisco FTD REST / CLI)
  - 172.23.70.89 (F5 iControl REST API)
- **Successful Connections (5):**
  - FORTIGATE (FortiGate CLI / REST API)
  - CISCO (Cisco IOS-XE SSH)
  - FMC (Cisco FMC REST API)
  - FTD (Cisco FTD REST / CLI)
  - F5 (F5 iControl REST API)
- **Failed Connections (0):**
  - None (100% Reachable)

## 🔬 Evidence Collected & Source Attribution
- [★★★★☆ (Vendor API)] Source: FortiGate CLI / REST API — Telemetry for FG-MNE-HQ retrieved.
- [★★★★★ (Live Device CLI)] Source: Cisco IOS-XE SSH — Telemetry for sw-cisco-core-01 retrieved.
- [★★★★☆ (Vendor API)] Source: Cisco FMC REST API — Telemetry for 172.23.70.77 retrieved.
- [★★★★☆ (Vendor API)] Source: Cisco FTD REST / CLI — Telemetry for 172.23.70.78 retrieved.
- [★★★★☆ (Vendor API)] Source: F5 iControl REST API — Telemetry for 172.23.70.89 retrieved.

## 📉 Knowledge Drift Analysis
- **Detected Drift Items:** 0 Discrepancies
- **Knowledge Alignment Score:** 0.99 / 1.0 (VERIFIED)

## 📁 File Processing Summary
- **Files Created:**
  - `operations/discovery/2026-07-25-network-discovery.md`
- **Files Updated:**
  - Canonical notes in `knowledge/` verified up-to-date.
- **Files Skipped:** 0

## ⚠️ Warnings & Engineering Recommendations
- Zero execution warnings recorded.
- All collected telemetry matches existing `knowledge/` canonical notes.
