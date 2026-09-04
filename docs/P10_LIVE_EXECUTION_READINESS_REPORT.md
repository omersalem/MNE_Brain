# P10 Real Live Execution Readiness Report

Date: 2026-08-27 (Africa/Cairo)

## Safety boundary reached

Real transport code, exact command/API rendering, per-binding readiness, and GUI/API status are implemented. Global P10 writes remain disabled. No infrastructure write, write-authentication attempt, or rollback was submitted.

The first real write test is blocked because none of the configured P7 bindings has a separate P10 write credential reference, username, and password. A P7 read credential is never treated as write authorization.

## Live read-only discovery

The registered P7 authenticated baseline was run with raw output and credentials suppressed:

- 32 active bindings checked.
- 29 succeeded.
- `p7-fmc`: `AUTHENTICATION_FAILED` over SSH. The independent pinned FMC REST binding succeeded.
- `p7-switch-tulkarm`: `TARGET_OR_IDENTITY_NOT_CONFIGURED`.
- `p7-vcenter-rest`: `AUTHORIZATION_FAILED`. The independent pinned vCenter SSH binding succeeded.
- One owner-excluded binding was not probed.

This proves point-in-time read transport status only. It does not prove write privilege.

## Supported-platform inventory

| Platform | Binding | Exact target | Identity reference | P7 live read | P10 write credential reference | Write authorization |
|---|---|---|---|---|---|---|
| fortinet_fortios | p7-fortigate-edge | 172.23.70.4 | MNE_FORTIGATE_SSH_HOSTKEY | SUCCESS | MNE_FORTIGATE_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| fortinet_fortios | p7-fortigate-bethlehem | 10.60.18.1 | MNE_FORTIGATE_BETHLAHEM_SSH_HOSTKEY | SUCCESS | MNE_FORTIGATE_BETHLAHEM_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| fortinet_fortios | p7-fortigate-hebron | 10.40.18.1 | MNE_FORTIGATE_HEBRON_SSH_HOSTKEY | SUCCESS | MNE_FORTIGATE_HEBRON_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| fortinet_fortios | p7-fortigate-hebron-gold | 10.40.19.1 | MNE_FORTIGATE_HEBRON_GOLD_SSH_HOSTKEY | SUCCESS | MNE_FORTIGATE_HEBRON_GOLD_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| fortinet_fortios | p7-fortigate-jenin | 10.201.18.1 | MNE_FORTIGATE_JENIN_SSH_HOSTKEY | SUCCESS | MNE_FORTIGATE_JENIN_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| fortinet_fortios | p7-fortigate-jericho | 10.211.18.1 | MNE_FORTIGATE_JERICHO_SSH_HOSTKEY | SUCCESS | MNE_FORTIGATE_JERICHO_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| fortinet_fortios | p7-fortigate-nablus | 10.131.18.1 | MNE_FORTIGATE_NABLUS_SSH_HOSTKEY | SUCCESS | MNE_FORTIGATE_NABLUS_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| fortinet_fortios | p7-fortigate-nablus-gold | 10.131.19.1 | MNE_FORTIGATE_NABLUS_GOLD_SSH_HOSTKEY | SUCCESS | MNE_FORTIGATE_NABLUS_GOLD_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| fortinet_fortios | p7-fortigate-qalqilya | 10.180.18.1 | MNE_FORTIGATE_QALQILYA_SSH_HOSTKEY | SUCCESS | MNE_FORTIGATE_QALQILYA_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| fortinet_fortios | p7-fortigate-quds | 10.70.18.1 | MNE_FORTIGATE_QUDS_SSH_HOSTKEY | SUCCESS | MNE_FORTIGATE_QUDS_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| fortinet_fortios | p7-fortigate-ramallah-gold | 10.110.19.1 | MNE_FORTIGATE_RAMALLAH_GOLD_SSH_HOSTKEY | SUCCESS | MNE_FORTIGATE_RAMALLAH_GOLD_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| fortinet_fortios | p7-fortigate-salfeet | 10.235.18.1 | MNE_FORTIGATE_SALFEET_SSH_HOSTKEY | SUCCESS | MNE_FORTIGATE_SALFEET_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| fortinet_fortios | p7-fortigate-tubas | 10.230.18.1 | MNE_FORTIGATE_TUBAS_SSH_HOSTKEY | SUCCESS | MNE_FORTIGATE_TUBAS_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| fortinet_fortios | p7-fortigate-tulkarem | 10.165.18.1 | MNE_FORTIGATE_TULKAREM_SSH_HOSTKEY | SUCCESS | MNE_FORTIGATE_TULKAREM_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| f5_bigip | p7-f5 | 172.23.70.89 | MNE_F5_SSH_HOSTKEY | SUCCESS | MNE_F5_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| cisco_fmc | p7-fmc | 172.23.70.77 | MNE_FMC_SSH_HOSTKEY | AUTHENTICATION_FAILED | MNE_FMC_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| cisco_fmc | p7-fmc-rest | 172.23.70.77 | MNE_FMC_TLS_CERT_SHA256 | SUCCESS | MNE_FMC_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| windows_powershell | p7-ad-primary | MNE-DC1.mne.gov | MNE-DC1.mne.gov (Kerberos SPN) | SUCCESS | MNE_AD_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| windows_powershell | p7-ad-secondary | MNE-DC2.mne.gov | MNE-DC2.mne.gov (Kerberos SPN) | SUCCESS | MNE_AD_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| windows_powershell | p7-exchange-primary | EXCHAMGESRV2.mne.gov | EXCHAMGESRV2.mne.gov (Kerberos SPN) | SUCCESS | MNE_EXCHANGE_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| windows_powershell | p7-exchange-ps | EXCHAMGESRV2.mne.gov | EXCHAMGESRV2.mne.gov (Kerberos SPN) | SUCCESS | MNE_EXCHANGE_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| vmware_vcenter | p7-vcenter | 172.23.69.38 | MNE_VCENTER_SSH_HOSTKEY | SUCCESS | MNE_VCENTER_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| vmware_vcenter | p7-vcenter-rest | 172.23.69.38 | MNE_VCENTER_TLS_CERT_SHA256 | AUTHORIZATION_FAILED | MNE_VCENTER_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| cisco_switching | p7-cisco-core | 172.23.70.254 | MNE_CISCO_SSH_HOSTKEY | SUCCESS | MNE_CISCO_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| cisco_switching | p7-router-tulkarm | 10.165.18.2 | MNE_ROUTER_TULKARM_SSH_HOSTKEY | SUCCESS | MNE_ROUTER_TULKARM_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| cisco_switching | p7-switch-tulkarm | NOT_CONFIGURED | MNE_SWITCH_TULKARM_SSH_HOSTKEY | TARGET_OR_IDENTITY_NOT_CONFIGURED | MNE_SWITCH_TULKARM_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| fujitsu_switching | p7-fujitsu-sw1 | 172.23.70.70 | MNE_SAN_SSH_HOSTKEY | SUCCESS | MNE_SAN_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |
| linux_host | p7-linux-greenunit | 172.23.79.200 | MNE_LINUX_SSH_HOSTKEY | SUCCESS | MNE_LINUX_WRITE_CREDENTIAL_REF | NOT_CONFIGURED |

## Registered but not P10-supported

- `p7-ftd` (172.23.70.78): direct managed-FTD writes remain prohibited; changes must go through FMC REST.
- `p7-sophos` (172.23.71.39): no reviewed P10 operation or driver.
- `p7-switch-hebron-gold` (10.40.19.3): Zyxel driver not implemented.
- `p7-switch-nablus-gold` (10.131.19.3): Zyxel driver not implemented.
- `p7-switch-ramallah-gold` (10.110.19.3): owner-excluded and its identity pin is not configured.

## Renderer coverage

The reviewed catalog contains 176 actions. Exact live rendering is currently available for 87 actions; 33 of those also have a deterministic rollback rendering. The remaining 89 actions fail closed because their generic catalog parameters do not contain enough exact object IDs, typed request fields, prior-state data, or bounded file/package content. They remain visible through `GET /api/p10/readiness` as blocked actions and cannot be submitted.

| Platform | Forward rendered | Rollback rendered | Blocked |
|---|---:|---:|---:|
| FortiGate | 24 | 13 | 9 |
| F5 BIG-IP | 17 | 6 | 14 |
| Cisco FMC | 5 | 0 | 12 |
| Windows PowerShell | 13 | 4 | 15 |
| VMware vCenter | 2 | 2 | 15 |
| Cisco switching/routing | 10 | 3 | 6 |
| Fujitsu switching | 10 | 3 | 6 |
| Linux | 6 | 2 | 12 |

## Execution sequence after the blocker is resolved

1. Configure an opaque separate write credential reference and separate username/password for one exact binding.
2. Run the platform-specific read-only privilege probe; authentication alone is not authorization.
3. Keep global P10 disabled until that one platform and target pass identity, authorization, exact state probe, renderer, rollback, and post-check validation.
4. Present exact target, commands/API request, risk, prechecks, postchecks, rollback, and out-of-band recovery.
5. Wait for the exact five-minute single-use owner approval phrase.
6. Submit once with no retry, independently read the resulting state, and report success only when the expected effect is verified.

## First real write test

Not started. Per the owner instruction, work stops before the first real write. The next required external input is a deliberately selected low-risk target plus its separate P10 write credential reference. Restarting the GUI is also deferred because active conversations are in memory and the owner must be warned/export them first.

## Validation

- `python -m pytest -q`: 231 passed.
- P10 focused mocked live transport, authorization, state, failure, and rollback tests: 77 passed.
- Schema/ADR validator: 57 contracts passed.
- Master validator: 22/22 gates passed.
- GUI JavaScript syntax: 10 modules passed.
- `git diff --check`: passed; line-ending notices only.
- Ignored `.env`: confirmed untracked; no credential-shaped value was found in the new P10 source, GUI, config, or report files.
