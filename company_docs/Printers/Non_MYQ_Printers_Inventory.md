# standalone / Non-MYQ Network Printers Inventory

This document tracks local and departmental network printers that are connected directly to the Ministry network but are **not** managed by the MYQ server.

---

## Standalone Printers Database

| Printer Name | IP Address | Model | Location | VLAN | Connection Type | Status |
|---|---|---|---|---|---|---|
| MNE-PRN-IT | `172.23.90.10` | HP LaserJet Enterprise M608 | 3rd Floor - IT Dept | 90 | Direct IP (LPR) | Active |
| MNE-PRN-FIN | `172.23.90.11` | Canon imageRUNNER C3226i | 2nd Floor - Finance Dept | 90 | Direct IP (Port 9100) | Active |
| MNE-PRN-HR | `172.23.90.12` | HP LaserJet Pro M404dn | 1st Floor - HR Office | 90 | Direct IP (LPR) | Active |
| MNE-PRN-MIN | `172.23.90.20` | Xerox VersaLink C405 | 4th Floor - Minister's Office | 90 | Direct IP (Port 9100) | Active |
| MNE-PRN-ARCH | `172.23.90.30` | HP ScanJet Enterprise Flow | Ground Floor - Archive Room | 90 | Direct IP (LPR) | Active |
| MNE-PRN-REG1 | `172.23.90.41` | Brother HL-L6400DW | Ground Floor - Registry | 90 | Direct IP (Port 9100) | Active |
| MNE-PRN-NABLUS| `172.23.102.10`| Canon imageRUNNER 2625i | Nablus Branch Office | 102 | Direct IP (Branch Route) | Active |

---

## Standalone Printers VLAN Architecture
- All core standalone network printers are assigned to **VLAN 90 (Printers Network)** on the subnet `172.23.90.0/24`.
- Branch printers are located in their respective branch subnets (e.g. `172.23.102.0/24` for Nablus Branch).
- Inter-VLAN routing is controlled by the FortiGate firewall (FG-MNE-B) which permits printer traffic (TCP Ports 9100, 515, 631) from employee subnets (VLANs 19-26) to VLAN 90.

---

## Diagnostic Procedures for Non-MYQ Printers

When an employee reports they cannot print to a standalone printer:
1. **Ping Test:** Ping the printer IP from the IT Tools Server (or within the network). If no response:
   - Check if printer is powered on and network cable is connected.
   - Verify if switch port is up (Core Switch / Aggregation Switch port status).
2. **Web Administrative Panel:** Attempt to connect to the printer's Web UI via `http://{IP_ADDRESS}`.
   - Verify paper supply, toner level, and check for active jams or open cover warnings.
3. **SNMP Status Check:** Query status using SNMP walk/get:
   - OID `1.3.6.1.2.1.25.3.5.1.1` (hrPrinterStatus)
     - `1` = Other
     - `2` = Unknown
     - `3` = Idle (Healthy)
     - `4` = Printing
     - `5` = Warmup
   - OID `1.3.6.1.2.1.25.3.5.1.2` (hrPrinterDetectedErrorState) for error flags.
