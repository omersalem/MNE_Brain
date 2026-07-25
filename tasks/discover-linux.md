# Task: Discover Linux Workloads

## Target Infrastructure
- **Greenunit ABRS Linux Server:** `srv-linux-abrs-01` (`172.23.79.200`, Ubuntu 22.04 LTS)
- **Linux Workload Pool:** Nginx, PHP 8.3, MariaDB, Cockpit management

## Execution Steps
1. Load Layer 1 notes from `knowledge/20_compute_and_virtualization/23_linux_servers/`.
2. Connect via OpenSSH read-only session (`172.23.79.200`).
3. Collect kernel details, systemd active services, disk mount usage (`df -h`), and listening network ports (`ss -tulpn`).
4. Detect package updates, unexpected open ports, or service state changes.
5. Update canonical notes in `knowledge/20_compute_and_virtualization/23_linux_servers/`.
6. Output discovery report to `operations/discovery/YYYY-MM-DD-linux-discovery.md`.
