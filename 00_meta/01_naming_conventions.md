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
