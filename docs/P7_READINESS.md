# P7 Readiness

Transport implementation now covers 48/48 canonical entities across SSH, REST, PowerShell, WinRM, VMware, SNMP, and TCP preflight boundaries. The 2026-08-16 live preflight covered the prior 46-entity set; the Tulkarm router and access switch now have exact owner-scoped bindings but remain unverified until a new approved live read succeeds. All transports are disabled at rest.

Live reachability is not device identity. Conflicting targets require an SSH key, TLS certificate, Kerberos identity, or SNMP engine identity plus platform/hostname validation before evidence can be accepted. Missing trust pins, credentials, dependencies, or reachability are reported as blockers rather than treated as success.

As of 2026-08-24, the catalog contains 33 bindings: 32 active and the sole-owner-excluded Ramallah Gold switch. The active set contains 26 pinned SSH, two pinned REST, and four Kerberos PowerShell/WinRM bindings. The original baseline and later targeted validations remain historical evidence; the newly registered Tulkarm switch scope has not been live-run. DC2 WinRM, vCenter object authorization, and FMC API authorization remain truthful blockers. Live policy remains disabled at rest, and each GUI execution requires an exact five-minute single-use owner phrase.
