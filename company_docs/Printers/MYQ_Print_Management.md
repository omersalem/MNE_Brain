# MYQ Print Management System Documentation

## System Overview
- **Server Name:** MYQ_SRV
- **IP Address:** `172.23.71.71` (VLAN 71 - Core Application Servers)
- **Port:** `80` (HTTP) / `443` (HTTPS)
- **Role:** Centralized print job queue management, badge release authentication, user printing quota tracking, and print accounting.

---

## Core Features
1. **Pull Printing (Secure Print Release):** Users send print jobs to a shared virtual queue and release them at any printer by scanning their RFID employee badge or typing their PIN.
2. **Quota Management:** Automatically tracks and enforces print page budgets for each department and individual staff member.
3. **Card Reader Authentication:** Integrates with physical card readers attached to MFP (Multi-Function Printer) devices.
4. **Queue Management:** Allows print administrators to view, delete, pause, or reschedule pending print jobs.

---

## Troubleshooting Workflows

### 1. User Cannot Print (General Issue)
- **Step 1: Check user account status in MYQ.** Query the user profile using the API/Admin interface. Ensure the account is not disabled or expired.
- **Step 2: Check print quota.** Check user quota balance. If the balance is `0` or negative, user cannot print. Allocate additional pages or reset the quota.
- **Step 3: Check print job queue.** Check if the job is stuck in the queue with status "Error" or "Paused". Purge stuck jobs if necessary.
- **Step 4: Check printer status.** Ensure the target printer is showing "Online" in MYQ and has no physical errors (paper jam, out of toner, tray open).

### 2. Print Job Stuck in Queue
- **Cause:** Corrupted print spooler file, offline printer, or print format mismatch.
- **Resolution:**
  - Locate the print job ID in the queue.
  - Delete the stuck job using the API/Admin interface.
  - Ask the user to re-submit the document as a standard PDF/Office document rather than raw image formats.

### 3. Quota Exhaustion
- **Cause:** User has exceeded their monthly page limit.
- **Resolution:**
  - Increase the quota limit for the user in MYQ.
  - In Write Mode, a command can be triggered to reset or allocate additional credit to the user's account.

---

## REST API Reference (For MNE Agent Use)

The MYQ Server exposes a REST API for automated administration and diagnostics.

| Endpoint | Method | Description |
|---|---|---|
| `/api/tokens` | POST | Authenticates using username/password, returns bearer token |
| `/api/v1/printers` | GET | Lists all managed printers and their current status |
| `/api/v1/printers/{id}` | GET | Returns details of a specific printer |
| `/api/v1/queues` | GET | Lists print queues and active jobs |
| `/api/v1/users/{username}` | GET | Returns user balance, quota, and assigned card ID |
| `/api/v1/users/{username}/quota` | POST | Adjusts or resets user's print quota balance (Write action) |
