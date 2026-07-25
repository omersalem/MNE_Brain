# Task: Discover Exchange Messaging Infrastructure

## Target Infrastructure
- **Exchange Servers:** `EXCHANGESRV1` (`172.23.71.35`), `EXCHANGESRV2` (`172.23.71.36`)
- **Database Availability Group:** `EXCH-DAG-MNE`
- **SSL Certificates & Virtual Directories:** OWA, ECP, Autodiscover, ActiveSync

## Execution Steps
1. Load Layer 1 notes from `knowledge/40_identity_and_core_services/43_messaging_and_mgmt/`.
2. Execute read-only Remote Exchange PowerShell EMS commands.
3. Collect DAG database copy status, mail queue depths, certificate expiration dates, and virtual directory URLs.
4. Detect Knowledge Drift in DAG active copies or expiring SSL certificates.
5. Update canonical notes in `knowledge/40_identity_and_core_services/43_messaging_and_mgmt/`.
6. Output discovery report to `operations/discovery/YYYY-MM-DD-exchange-discovery.md`.
