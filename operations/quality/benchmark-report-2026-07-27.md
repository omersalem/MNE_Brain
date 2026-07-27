# Benchmark Execution Report — 2026-07-27

- **Total Benchmark Scenarios:** 11
- **Passed:** 11
- **Failed:** 0
- **Pass Rate:** 100.0%

## 📊 Scenario Results Table
| ID | Scenario | Status | Route Actual | Route Expected | Remediation Gate |
|---|---|---|---|---|---|
| `scen-01-dns-mismatch` | DNS resolution mismatch | ✅ PASS | `troubleshooting` | `troubleshooting` | Yes |
| `scen-02-fortigate-policy` | FortiGate policy lookup | ✅ PASS | `health_check` | `health_check` | Yes |
| `scen-03-f5-pool-down` | F5 pool member unavailable | ✅ PASS | `troubleshooting` | `troubleshooting` | Yes |
| `scen-04-exchange-mailflow` | Exchange mail-flow failure | ✅ PASS | `troubleshooting` | `troubleshooting` | Yes |
| `scen-05-vmware-vm-down` | VMware VM unavailable | ✅ PASS | `health_check` | `health_check` | Yes |
| `scen-06-ssl-vpn-issue` | SSL-VPN issue | ✅ PASS | `troubleshooting` | `troubleshooting` | Yes |
| `scen-07-branch-outage` | Branch outage | ✅ PASS | `health_check` | `health_check` | Yes |
| `scen-08-slow-app` | Slow application | ✅ PASS | `troubleshooting` | `troubleshooting` | Yes |
| `scen-09-unknown-host` | Unknown hostname | ✅ PASS | `health_check` | `health_check` | Yes |
| `scen-10-stale-doc` | Stale documentation | ✅ PASS | `review` | `review` | Yes |
| `scen-11-remediation-gate` | Unsupported remediation request | ✅ PASS | `remediation` | `remediation` | Yes |