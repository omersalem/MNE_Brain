# Task: Discover Active Directory & Identity Services

## Target Infrastructure
- **Domain Controllers:** `MNE-DC1` (`172.23.71.27`), `MNE-DC2` (`172.23.71.28`)
- **DNS Server:** `mne.gov.ps` Primary DNS Zone
- **DHCP Server:** User & Infrastructure DHCP Scopes
- **SCCM Server:** `sys-Cntre` (`172.23.71.84`)

## Execution Steps
1. Load Layer 1 notes from `knowledge/40_identity_and_core_services/`.
2. Execute read-only LDAP queries and WinRM PowerShell commands.
3. Collect domain controller health, DNS zone records, DHCP lease scopes, and SCCM deployment policies.
4. Detect Knowledge Drift in DNS records or DHCP scope ranges.
5. Update canonical notes in `knowledge/40_identity_and_core_services/`.
6. Output discovery report to `operations/discovery/YYYY-MM-DD-identity-discovery.md`.
