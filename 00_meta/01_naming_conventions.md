# MNE_Brain Release 2 — Naming Conventions Specification

> **Status:** APPROVED ARCHITECTURE CONTRACT  
> **Path:** `00_meta/01_naming_conventions.md`  

---

## 🏛️ Standard Naming Rules across Release 2

To maintain total consistency, machine-readability, and clean maintainability across `MNE_Brain_v2`, all repository assets follow strict naming conventions.

### 1. File & Directory Naming Rules

| Asset Category | Folder Location | Naming Pattern | Example File Path |
| :--- | :--- | :--- | :--- |
| **JSON Schemas** | `00_meta/schemas/` | `<entity_type>.schema.json` | `00_meta/schemas/profile.schema.json` |
| **Architecture Decision Records** | `00_meta/adr/` | `ADR-<3-digit-number>-<kebab-case-title>.md` | `00_meta/adr/ADR-001-Independent-Projects.md` |
| **Declarative Profiles** | `profiles/` | `<platform-name>.yaml` | `profiles/fortigate.yaml` |
| **Task Specifications** | `tasks/` | `<verb>-<noun>.md` | `tasks/discover-network.md` |
| **Canonical Knowledge Notes** | `knowledge/<domain>/` | `<device-or-topic>-canonical.md` | `knowledge/topology/fortigate-canonical.md` |
| **Operational Telemetry Logs** | `operations/verification/` | `<device>-<check-id>-<YYYY-MM-DD>.txt` | `operations/verification/fw-01-system-status-2026-08-01.txt` |
| **Remediation Action Templates**| `actions/approved/` | `<risk-level>-<action-id>.yaml` | `actions/approved/level2-toggle-f5-member.yaml` |
| **Python Script Modules** | `core/<module>/` | `<snake_case_name>.py` | `core/router/route_query.py` |
| **Protocol Drivers** | `core/tools/drivers/` | `<protocol_name>_driver.py` | `core/tools/drivers/ssh_driver.py` |

---

## 📐 2. Field & Property Key Rules

1. **YAML / JSON Keys:** Lowercase snake_case (`trust_level`, `target_file`, `normalize_policy`).
2. **Environment Variable Keys:** Uppercase snake_case with domain prefix (`FORTIGATE_HOST`, `VMWARE_VCENTER_IP`).
3. **Markdown Headings:** H1 (`#`) for main title, H2 (`##`) for section, H3 (`###`) for sub-element.

---

## 🛡️ 3. FortiGate Firewall Policy & Object Naming Grammar

All firewall policies and objects on enterprise firewalls (`FG-MNE`) conform to the following deterministic grammar:

### 3.1 Firewall Policy Naming Patterns

1. **Active Policies:**
   ```
   P_<ORIGIN>_TO_<DESTINATION>_<ACTION>[_<MODIFIER>]
   ```
   - `P_`: Prefix indicating a firewall policy (`config firewall policy`).
   - `<ORIGIN>`: Source security zone, network segment, or entity (e.g. `USR`, `FLR1`, `BISAN`, `BRN`, `VPN`, `DMZ`).
   - `TO`: Directional delimiter.
   - `<DESTINATION>`: Destination security zone, network segment, or entity (e.g. `SRV`, `WAN`, `INET`, `PRN`, `SCN`, `ORACLE`).
   - `<ACTION>`: Action type (`A` for Accept, `D` for Deny).
   - `[_<MODIFIER>]`: Optional semantic qualifier for disambiguation (e.g. `KASPER`, `SP114`, `TRADE212`, `SMB`).
   - *Example:* `P_USR_TO_SRV_KASPER_A`, `P_BISAN_TO_SCN_SCANER_A`

2. **Disabled / Quarantined Policies:**
   ```
   P_DIS_<ORIGIN>_TO_<DESTINATION>_<ACTION>[_<MODIFIER>]
   ```
   - `P_DIS_`: Prefix indicating an administratively disabled firewall policy (`set status disable`).
   - Retains the full source-to-destination semantic lineage while explicitly flagging inactive status for auditing and lifecycle management.
   - *Example:* `P_DIS_BEET_TO_MAIL_A`, `P_DIS_IT_TO_CISCOFMC_A`, `P_DIS_VPN_TO_SRV_HANAN_A`

### 3.2 Address & Service Group Naming Patterns

- **Address Groups:** `AG_<TYPE>_<NAME>` (e.g. `AG_SRV_CORE_INFRA`, `AG_FLR_ALL_PRINTERS`)
- **Service Groups:** `SG_<PURPOSE>_<FUNCTION>` (e.g. `SG_PRINT_DIRECT`, `SG_SCAN_SMB`, `SG_MGMT_WEB`)
