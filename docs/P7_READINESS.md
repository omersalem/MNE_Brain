# P7 Readiness

As of 2026-08-16, transport implementation covers 46/46 canonical entities across SSH, REST, PowerShell, WinRM, VMware, SNMP, and TCP preflight boundaries. All transports are disabled at rest.

Live reachability is not device identity. Conflicting targets require an SSH key, TLS certificate, Kerberos identity, or SNMP engine identity plus platform/hostname validation before evidence can be accepted. Missing trust pins, credentials, dependencies, or reachability are reported as blockers rather than treated as success.

As of 2026-08-18, the catalog contains 32 bindings: 31 active and the sole-owner-excluded Ramallah Gold switch. The active set contains 25 pinned SSH, two pinned REST, and four Kerberos PowerShell/WinRM bindings. The original 27-binding baseline was completed; targeted validation then confirmed Fujitsu SW1 and Exchange PowerShell. DC2 WinRM, vCenter object authorization, and FMC API authorization remain truthful blockers. Live policy remains disabled at rest, and each future session still requires an explicit owner `proceed` instruction.
