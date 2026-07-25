# Infrastructure Brain — Self-Hosted GitHub Runner Setup Guide

> **Machine Target:** Permanent Windows Server (IP: `172.23.50.62`)  
> **Repository Target:** `https://github.com/omersalem/MNE_Brain`  
> **Operating Mode:** 24/7 Autonomous Infrastructure Discovery & Sync

---

## 📋 Prerequisites & Software Requirements

1. **Operating System:** Windows Server 2019 / 2022 or Windows 10/11 (Power-on 24/7).
2. **Network Connectivity:** Direct read-only IP access to Ministry network subnets (`172.23.70.x`, `172.23.71.x`, `172.23.69.x`, `172.23.79.x`).
3. **Software Packages to Install:**
   - **Git for Windows:** Download from [git-scm.com](https://git-scm.com/download/win).
   - **Python 3.11+:** Download from [python.org](https://www.python.org/downloads/). Ensure **"Add python.exe to PATH"** is checked.
   - **Powershell 7+:** (Default Windows PowerShell 5.1+ is also supported).

---

## 🚀 Step 1: Install & Register GitHub Actions Runner

1. Log into machine `172.23.50.62` as an Administrator.
2. Open PowerShell as Administrator and create the runner directory:
   ```powershell
   New-Item -ItemType Directory -Path "C:\actions-runner" -Force
   Set-Location "C:\actions-runner"
   ```

3. Download the latest runner package:
   ```powershell
   Invoke-WebRequest -Uri "https://github.com/actions/runner/releases/download/v2.317.0/actions-runner-win-x64-2.317.0.zip" -OutFile "runner.zip"
   Expand-Archive -Path "runner.zip" -DestinationPath "." -Force
   Remove-Item "runner.zip"
   ```

4. Obtain a Registration Token from GitHub:
   - Open browser to **[https://github.com/omersalem/MNE_Brain/settings/actions/runners/new](https://github.com/omersalem/MNE_Brain/settings/actions/runners/new)**.
   - Copy the token generated under **Configure**.

5. Register the Runner:
   ```powershell
   .\config.cmd --url https://github.com/omersalem/MNE_Brain --token <YOUR_RUNNER_REGISTRATION_TOKEN> --name "MNE-BRAIN-RUNNER-62" --work "_work" --labels "self-hosted,windows,172.23.50.62" --unattended
   ```

---

## ⚙️ Step 2: Configure Windows Service for 24/7 Reboot Startup

To ensure discovery workflows run automatically after system reboots without manual login:

```powershell
Set-Location "C:\actions-runner"
.\svc.cmd install
.\svc.cmd start
```

Verify service status:
```powershell
Get-Service "actions.runner.*"
```
The status should be **`Running`**.

---

## 🐍 Step 3: Install Required Python Libraries

Open PowerShell as Administrator and install required read-only discovery libraries:

```powershell
pip install requests urllib3 paramiko pyvmomi pandas
```

---

## 🧪 Step 4: Validate Runner Connection

1. Go to **[https://github.com/omersalem/MNE_Brain/settings/actions/runners](https://github.com/omersalem/MNE_Brain/settings/actions/runners)**.
2. Verify that **`MNE-BRAIN-RUNNER-62`** appears with status **`Idle`** (Active & Ready).
3. Execute any workflow manually from **GitHub Actions $\rightarrow$ Run workflow** to test end-to-end automated discovery.

---

## 🔄 Updating & Maintaining the Runner

- **Automatic Updates:** GitHub Actions Runner updates itself automatically when GitHub releases a new version.
- **Restarting Service:** If network credentials or environment variables change, restart the service:
  ```powershell
  Set-Location "C:\actions-runner"
  .\svc.cmd stop
  .\svc.cmd start
  ```
