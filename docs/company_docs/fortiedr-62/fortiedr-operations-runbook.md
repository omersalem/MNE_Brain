---
runbook_id: "fortiedr-endpoint-triage"
title: "FortiEDR Cloud Endpoint Security and Incident Evidence Triage"
version: "1.0.0"
status: "operationally_reviewed"
runbook_type: "domain_troubleshooting"
scope_categories: ["network", "application"]
scope_services: ["edr-management", "endpoint-prevention", "threat-hunting", "communication-control", "collector-registration"]
scope_entity_ids: ["edr-fortiedr-cloud-01"]
category_fallback_allowed: false
owner_team: "MNE-BRAIN-OWNER"
requires_exact_target: true
live_access_allowed: false
remediation_allowed: false
evidence_objectives: ["confirm-reported-endpoint", "collect-collector-registration-status", "collect-security-event-classification", "collect-process-lineage-and-hash", "collect-network-connection-evidence", "collect-policy-prevention-mode"]
stop_conditions: ["Exact target endpoint or incident context is unknown", "The owner has not explicitly said proceed for read-only collection", "Console visibility is treated as proof of endpoint remediation without fresh evidence", "Remediation, isolation, process kill, or policy modification is proposed without explicit owner instruction", "Evidence is stale, simulated, or cross-target"]
source_basis: "owner_review"
review_sources: ["fortiedr-canonical.md", "fortiedr-gui-administration-guide.md", "fortiedr-cli-collector-guide.md"]
operational_boundary: "PROCEDURE_REVIEWED_LIVE_STATE_UNVERIFIED"
last_reviewed: "2026-09-12"
---

# FortiEDR Cloud Endpoint Security and Incident Evidence Triage

## Purpose

Use this operational standard operating procedure (SOP) when investigating an endpoint security event, malware alert, communication anomaly, or collector connectivity issue reported within the FortiEDR 6.2 platform for organization **MNE**. The Central Manager console (`https://fortiedrconnectil.console.ensilo.com`) provides visibility into endpoint security events and telemetry.

---

## Operational SOP Workflows

### SOP-EDR-01: Incident Triage & Endpoint Quarantine
1. **Identify Alert in Event Viewer:**
   - Locate the alert under `EVENT VIEWER`. Verify timestamp, endpoint hostname, logged-in user, and classification.
2. **Analyze Process Hierarchy (Event Graph):**
   - Click the event to open `Event Graph`. Identify the root parent process (e.g. `explorer.exe` -> `powershell.exe` -> suspicious binary).
   - Note the SHA-256 hash, command-line arguments, and code injection targets.
3. **Execute Network Isolation:**
   - If the threat is actively attempting lateral movement or outbound C2 communication, select `Actions > Isolate Device`.
   - The collector instantly terminates all external IP communication while preserving the encrypted management tunnel over port `8081` to the Aggregator.
4. **Remediate the Endpoint:**
   - Select `Actions > Remediate Device`.
   - Check `Kill Process`, `Delete File`, `Quarantine File`, and `Clean Persistence`. Click `Apply Remediation`.

---

### SOP-EDR-02: Live Forensics & Evidence Retrieval (FortiEDR Connect)
1. **Establish Remote Live Shell:**
   - In `EVENT VIEWER` or `INVENTORY`, select the affected device and click `FortiEDR Connect`.
   - An interactive, encrypted command-line session opens directly inside the console.
2. **Acquire Volatile Artifacts:**
   - Run memory acquisition via `Retrieve Memory` to dump process memory or physical RAM.
   - Use `File Library` to upload forensic investigation scripts or download suspicious dropped files for external sandbox detonation.

---

### SOP-EDR-03: Mass Collector Deployment via GPO / SCCM
1. **Prepare MSI Package & Parameters:**
   - Place `FortiEDRCollectorInstaller64.msi` on the network distribution share.
2. **Execute Silent Installation Command:**
   ```powershell
   msiexec.exe /i "\\mne-dc1\share\FortiEDRCollectorInstaller64.msi" /qn `
     AGG=fortiedrconnectil.console.ensilo.com:8081 `
     PWD="<RegistrationPassword>" `
     ORG="MNE" `
     DEFGROUP="Default Collector Group" `
     /log "C:\Windows\Temp\fortiedr_install.log"
   ```
3. **Verify Service State:**
   ```powershell
   Get-Service -Name FortiEDRCollectorService | Select-Object Name, Status, StartType
   ```

---

### SOP-EDR-04: False Positive Tuning (Exceptions vs Exclusions)
1. **Adding Security Event Exception (Event Viewer):**
   - Click `Actions > Add Exception` on the false-positive alert.
   - Scope: Set to `Collector Group` or Organization `MNE`.
   - Match by: Digital Signer / Certificate or SHA-256 Hash.
2. **Adding Folder / Process Exclusion (Security Settings):**
   - Navigate to `SECURITY SETTINGS > Exclusion Manager`.
   - Click `Add Exclusion`. Add folder path or process path (e.g. internal line-of-business application directory) and save.

---

### SOP-EDR-05: Lucene Threat Hunting Queries (Forensics Tab)
Under `FORENSICS`, enter targeted Lucene queries across historical endpoint logs:
- Find suspicious PowerShell encoded commands:
  ```lucene
  Process.name:"powershell.exe" AND Process.commandLine:*-enc*
  ```
- Find unauthorized outbound network connections on non-standard ports:
  ```lucene
  Connection.direction:"Outbound" AND NOT Connection.destinationPort:(80 OR 443 OR 53)
  ```
- Find ransomware persistence in Run keys:
  ```lucene
  Registry.key:*"CurrentVersion\\Run"*
  ```
