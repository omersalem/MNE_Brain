# Task: Discover Network Devices

## Target Infrastructure
- **FortiGate HQ & Branch Firewalls:** `172.23.70.4`, Branch FortiGates (`.1`)
- **Cisco Core Stack & Access Switches:** `172.23.70.254`, `172.23.70.221`, Branch Access (`.3`)
- **Cisco FMC & FTD:** `172.23.70.77`, `172.23.70.78`
- **F5 BIG-IP WAF:** `172.23.70.89`

## Execution Steps
1. Load Layer 1 notes from `knowledge/10_network_and_security/`.
2. Connect using read-only API/SSH credentials from `00_meta/05_connections/`.
3. Collect live interface, ARP, routing, policy, and virtual server telemetry.
4. Normalize data using `00_meta/framework/normalizer.py`.
5. Compare live telemetry with `knowledge/10_network_and_security/` to detect Knowledge Drift.
6. Update `knowledge/` Markdown canonical notes.
7. Output discovery report to `operations/discovery/YYYY-MM-DD-network-discovery.md`.
