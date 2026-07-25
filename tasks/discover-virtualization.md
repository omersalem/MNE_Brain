# Task: Discover Virtualization Infrastructure

## Target Infrastructure
- **vCenter Appliance:** `172.23.69.38` (vSphere 7.0.3)
- **ESXi Hosts:** `172.23.69.41` to `172.23.69.44`
- **Clusters & Datastores:** Production VMware Cluster & NFS Datastores
- **Virtual Machines:** 148 Total Guest VMs

## Execution Steps
1. Load Layer 1 notes from `knowledge/20_compute_and_virtualization/21_vcenter_and_hosts/`.
2. Connect to vCenter REST API using read-only service account.
3. Collect live ESXi host state, CPU/RAM allocation, VM power states, and datastore usage.
4. Compare live telemetry with vault notes to detect VM additions or host reallocations.
5. Update canonical notes in `knowledge/20_compute_and_virtualization/`.
6. Output discovery report to `operations/discovery/YYYY-MM-DD-virtualization-discovery.md`.
