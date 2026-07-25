# Task: Discover SAN Storage & Storage Switches

## Target Infrastructure
- **Fujitsu SAN ETERNUS:** `san-fujitsu-eternus-01` (`172.23.69.100`)
- **Fibre Channel Switches:** `fc-sw-fujitsu-01` (`172.23.69.101`)

## Execution Steps
1. Load Layer 1 notes from `knowledge/30_storage/`.
2. Connect to Fujitsu ETERNUS CLI/API using read-only credentials.
3. Collect RAID group health, thin provisioning pool allocation, SAN volumes, LUN masking, and FC switch port statuses.
4. Detect storage pool capacity drift or degraded LUN paths.
5. Update canonical notes in `knowledge/30_storage/`.
6. Output discovery report to `operations/discovery/YYYY-MM-DD-storage-discovery.md`.
