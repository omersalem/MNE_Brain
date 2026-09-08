# FortiAnalyzer 7.4.10 — Storage Quotas & Log Retention Architecture

This guide explains how FortiAnalyzer 7.4.10 manages storage quotas, log retention policies, database partitioning, and how to safely expand disk allocations.

---

## 1. Storage Architecture: Analytics vs. Archive

FortiAnalyzer partitions log storage into two distinct data stores:

| Storage Type | Format | Engine | Purpose | Resource Footprint |
|---|---|---|---|---|
| **Analytics (Indexed)** | Structured Tables | SQL Database (PostgreSQL engine) | Powering **Log View**, **FortiView**, and generating **Reports**. Fast queries and search. | Higher disk I/O, consumes index space (~60–70% of quota). |
| **Archive (Raw Logs)** | Compressed Text Files (`.log.gz`) | Ext4 Flat Filesystem | Long-term compliance, historical audits, forensic log recovery. | Low I/O, high compression (~30–40% of quota). |

---

## 2. The Golden Rule: Storage Quota Always Trumps Retention Days

> [!CAUTION]
> If an ADOM's storage quota is reached, **FortiAnalyzer immediately deletes the oldest logs to free up space**, even if the configured retention time (e.g. 180 days) has not been reached!

### Current MNE Deployment Audit:
- **Total Virtual Disk:** `491.1 GB`
- **Total Quota Available for ADOMs:** `441.1 GB`
- **Allocated to ADOM `root`:** `63.0 GB` (Only 14.3% of disk allocated!)
- **Unallocated Space:** `378.1 GB` (Sitting idle)
- **Current Utilization of Allocated Quota:**
  - **Analytics (SQL Database):** `40.3 GB` used out of `44.1 GB` (**91.4% saturation**)
  - **Archive (Raw Logs):** `16.9 GB` used out of `18.9 GB` (**89.5% saturation**)

**Impact:** Because the SQL quota is at 91.4%, the system is actively at risk of rolling over and purging older event history prematurely, despite having over **378 GB of free, unallocated physical storage**.

---

## 3. How to Expand the ADOM Quota (Recommended Action)

To eliminate disk saturation and enable long-term compliance retention:

### Method 1: Via Web GUI (Fastest)
1. In the left navigation sidebar, click **`System Settings > ADOMs`**.
2. In the table under **`Security Fabric (1)`**, select the row **`[x] root`** (which shows `Allocated Storage: 63 GB`).
3. Click the **`[ Edit ]`** button in the top toolbar (or double-click `root`).
4. In the **`Edit ADOM - root`** modal on the right side:
   - You will see `Name`, `Type`, `Description`, and the `Devices` table.
   - ⚠️ **SCROLL DOWN INSIDE THE MODAL BODY** past the `Devices` list!
5. In the **`Data Policy`** section:
   - **Keep Logs for Analytics:** Change `[ 60 ]` to `[ 180 ]` Days.
   - **Keep Logs for Archive:** Change `[ 100 ]` to `[ 365 ]` Days.
6. In the **`Disk Utilization`** section:
   - **Allocated:** Change from `[ 63 ]` to **`[ 300 ]`** `[ GB ▾ ]` (utilizing the available 378 GB unallocated space).
   - **Analytics : Archive:** Set ratio to `70%` / `30%` (check the **`[ ] Modify`** box to edit).
   - **Alert and delete when usage reaches:** `90%`.
7. Click the blue **`[ OK ]`** button at the bottom of the modal.

### Method 2: Verifying via CLI
Run the diagnostic command:
```bash
diagnose log device
```
Verify that the `Total Quota Summary` reflects the new expanded quota and that `Used%` drops significantly (e.g. to ~20%).

---

## 4. Re-Indexing and Partition Maintenance

If logs exist in the Archive store but do not show up in Log View or Reports (e.g., after an unexpected reboot or disk expansion):

### Re-Index an ADOM
```bash
execute sql-local rebuild-adom root
```
*Prompts for confirmation and begins rebuilding the SQL indices in the background.*

### Monitor Indexing Progress
```bash
diagnose sql status rebuild-db
```

---

## 5. Automated External Archiving (NAS / SFTP Offload)

To archive raw logs off-appliance for infinite retention:
1. In the Web GUI, go to **System Settings > Advanced > Log Forwarding**.
2. Click **Create New**:
   - **Name:** `MNE-NAS-Archive`
   - **Server Type:** Syslog / CEF / FortiAnalyzer / File Server (SFTP).
   - **Server IP:** Target NAS / backup server IP.
   - **Schedule:** Realtime or Hourly.
3. Click **OK**.
