<#
.SYNOPSIS
    Registers and starts the MNE_Brain Presentation GUI & REST API server as a persistent Windows Service using NSSM.

.DESCRIPTION
    Configures the MNE_Brain server to run 24/7 as an automatic Windows Service.
    - Runs continuously even when no interactive user is logged on.
    - Automatically restarts within 5 seconds if terminated or crashed.
    - Redirects standard output and errors to rolling log files in operations/logs/.
    - Preserves user profile paths and environment variables so AI providers and tools resolve properly.

.EXAMPLE
    .\scripts\register_server_service.ps1
    .\scripts\register_server_service.ps1 -Force
#>

[CmdletBinding()]
param(
    [string]$ServiceName = "MNE_Brain_Server",
    [string]$DisplayName = "MNE_Brain Server (API & GUI)",
    [string]$Description = "MNE_Brain Release 2 Presentation GUI and REST API service running on port 8080.",
    [int]$Port = 8080,
    [string]$PythonPath = "",
    [string]$NssmPath = "",
    [string]$WorkingDir = "",
    [string]$UserProfile = "",
    [string]$LocalAppData = "",
    [string]$AppData = "",
    [string]$CodexPath = "",
    [string]$OpenCodePath = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# 1. Resolve Project Working Directory & Logs
if (-not $WorkingDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $WorkingDir = (Resolve-Path "$ScriptDir\..").Path
}
$LogsDir = Join-Path $WorkingDir "operations\logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

$StdoutLog = Join-Path $LogsDir "server_service.log"
$StderrLog = Join-Path $LogsDir "server_service_error.log"

# 2. Resolve User Profile & Environment Paths
if (-not $UserProfile) { $UserProfile = $env:USERPROFILE }
if (-not $LocalAppData) { $LocalAppData = $env:LOCALAPPDATA }
if (-not $AppData) { $AppData = $env:APPDATA }

# 3. Locate NSSM Executable
if (-not $NssmPath -or -not (Test-Path $NssmPath)) {
    $nssmCmd = Get-Command nssm.exe -ErrorAction SilentlyContinue
    if ($nssmCmd) {
        $NssmPath = $nssmCmd.Source
    } else {
        $wingetCandidates = Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WinGet\Packages", "C:\Users\*\AppData\Local\Microsoft\WinGet\Packages" -Filter "nssm.exe" -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.FullName -like "*win64*" }
        if ($wingetCandidates) {
            $NssmPath = ($wingetCandidates | Select-Object -First 1).FullName
        }
    }
}

if (-not $NssmPath -or -not (Test-Path $NssmPath)) {
    Write-Host "[*] NSSM not found. Attempting installation via winget..." -ForegroundColor Yellow
    try {
        & winget install NSSM.NSSM --accept-package-agreements --accept-source-agreements --silent
        $wingetCandidates = Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WinGet\Packages", "C:\Users\*\AppData\Local\Microsoft\WinGet\Packages" -Filter "nssm.exe" -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.FullName -like "*win64*" }
        if ($wingetCandidates) {
            $NssmPath = ($wingetCandidates | Select-Object -First 1).FullName
        }
    } catch {
        Write-Warning "Winget installation failed: $_"
    }
}

# 4. Locate Python Interpreter
if (-not $PythonPath -or -not (Test-Path $PythonPath)) {
    $pyCmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pyCmd) {
        $PythonPath = $pyCmd.Source
    } else {
        $hermesPy = "C:\Users\admin\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
        if (Test-Path $hermesPy) {
            $PythonPath = $hermesPy
        }
    }
}

# Resolve per-user AI binaries before elevation. LocalSystem does not inherit the
# owner's PATH, so the service receives explicit non-secret executable paths.
if (-not $CodexPath -or -not (Test-Path $CodexPath)) {
    $codexCmd = Get-Command codex.exe -ErrorAction SilentlyContinue
    if ($codexCmd) { $CodexPath = $codexCmd.Source }
    if (-not $CodexPath) {
        $codexCandidates = @(
            (Join-Path $LocalAppData "Programs\OpenAI\Codex\bin\codex.exe"),
            (Join-Path $LocalAppData "OpenAI\Codex\bin\codex.exe")
        )
        $CodexPath = $codexCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    }
}

if (-not $OpenCodePath -or -not (Test-Path $OpenCodePath)) {
    $openCodeNative = Join-Path $AppData "npm\node_modules\opencode-ai\bin\opencode.exe"
    if (Test-Path -LiteralPath $openCodeNative) {
        $OpenCodePath = $openCodeNative
    } else {
        $openCodeCmd = Get-Command opencode.exe -ErrorAction SilentlyContinue
        if ($openCodeCmd) { $OpenCodePath = $openCodeCmd.Source }
    }
}

# 5. Check for Administrator Privileges; elevate if necessary
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Yellow
    Write-Host " [!] Administrator privileges required to register Windows Service" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Yellow
    Write-Host "[*] Requesting elevation via UAC..." -ForegroundColor Cyan

    $argList = "-NoProfile -NoExit -ExecutionPolicy Bypass -File `"$PSCommandPath`" -WorkingDir `"$WorkingDir`" -UserProfile `"$UserProfile`" -LocalAppData `"$LocalAppData`" -AppData `"$AppData`""
    if ($Force) { $argList += " -Force" }
    if ($PythonPath) { $argList += " -PythonPath `"$PythonPath`"" }
    if ($NssmPath) { $argList += " -NssmPath `"$NssmPath`"" }
    if ($CodexPath) { $argList += " -CodexPath `"$CodexPath`"" }
    if ($OpenCodePath) { $argList += " -OpenCodePath `"$OpenCodePath`"" }

    Start-Process powershell.exe -Verb RunAs -WorkingDirectory $WorkingDir -ArgumentList $argList

    Write-Host ""
    Write-Host "If the UAC prompt appeared, click 'Yes' to complete the registration." -ForegroundColor Green
    Write-Host "Alternatively, open an elevated PowerShell prompt (Run as Administrator) and run:" -ForegroundColor White
    Write-Host "  cd $WorkingDir" -ForegroundColor Cyan
    Write-Host "  .\scripts\register_server_service.ps1" -ForegroundColor Cyan
    Write-Host ""
    exit 0
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " MNE_Brain Windows Service Registration (NSSM)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (-not $NssmPath -or -not (Test-Path $NssmPath)) {
    Write-Error "NSSM executable could not be located. Please specify -NssmPath."
    exit 1
}

if (-not $PythonPath -or -not (Test-Path $PythonPath)) {
    Write-Error "Python executable could not be found. Please specify -PythonPath."
    exit 1
}

Write-Host "[+] NSSM Binary:       $NssmPath" -ForegroundColor Green
Write-Host "[+] Python Binary:     $PythonPath" -ForegroundColor Green
Write-Host "[+] Working Directory: $WorkingDir" -ForegroundColor Green
Write-Host "[+] User Profile:      $UserProfile" -ForegroundColor Green
Write-Host "[+] Codex Binary:      $(if ($CodexPath) { $CodexPath } else { 'Not found' })" -ForegroundColor $(if ($CodexPath) { 'Green' } else { 'Yellow' })
Write-Host "[+] OpenCode Binary:   $(if ($OpenCodePath) { $OpenCodePath } else { 'Not found' })" -ForegroundColor $(if ($OpenCodePath) { 'Green' } else { 'Yellow' })

# 6. Check and Resolve Port Conflict on Port 8080
$activeConn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
if ($activeConn) {
    $conflictingPid = ($activeConn | Select-Object -First 1).OwningProcess
    $existingServiceCim = Get-CimInstance Win32_Service -Filter "Name='$ServiceName'" -ErrorAction SilentlyContinue
    $existingServicePid = if ($existingServiceCim) { [int]$existingServiceCim.ProcessId } else { 0 }
    try {
        $conflictingProc = Get-Process -Id $conflictingPid -ErrorAction SilentlyContinue
        $procName = if ($conflictingProc) { $conflictingProc.ProcessName } else { "Unknown" }
    } catch {
        $procName = "PID $conflictingPid"
    }

    if ($existingServicePid -ne $conflictingPid) {
        Write-Error "Port $Port is owned by unrelated process '$procName' (PID: $conflictingPid). Stop it explicitly or choose another port; this script will not terminate it."
        exit 1
    }
    Write-Host "[!] Port $Port is owned by the existing '$ServiceName' service (PID: $conflictingPid); it will be stopped through Service Control Manager." -ForegroundColor Yellow
}

# 7. Stop and Remove Existing Service if already present
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "[*] Service '$ServiceName' already exists. Stopping and updating..." -ForegroundColor Yellow
    if ($existingService.Status -eq "Running") {
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    & $NssmPath remove $ServiceName confirm 2>$null | Out-Null
    Start-Sleep -Seconds 1
}

# 8. Register Service via NSSM
Write-Host "[*] Installing service '$ServiceName' via NSSM..." -ForegroundColor Cyan
& $NssmPath install $ServiceName "$PythonPath" "gui/server.py"
if ($LASTEXITCODE -ne 0) {
    Write-Error "NSSM service install failed with exit code $LASTEXITCODE."
    exit 1
}

Write-Host "[*] Configuring service parameters..." -ForegroundColor Cyan
& $NssmPath set $ServiceName AppDirectory "$WorkingDir"
& $NssmPath set $ServiceName DisplayName "$DisplayName"
& $NssmPath set $ServiceName Description "$Description"
& $NssmPath set $ServiceName Start SERVICE_AUTO_START

# Logging configuration
& $NssmPath set $ServiceName AppStdout "$StdoutLog"
& $NssmPath set $ServiceName AppStderr "$StderrLog"
& $NssmPath set $ServiceName AppStdoutCreationDisposition 4
& $NssmPath set $ServiceName AppStderrCreationDisposition 4
& $NssmPath set $ServiceName AppRotateFiles 1
& $NssmPath set $ServiceName AppRotateOnline 1
& $NssmPath set $ServiceName AppRotateBytes 10485760

# Process recovery policy (restart after 5000ms delay if crashed)
& $NssmPath set $ServiceName AppRestartDelay 5000
& $NssmPath set $ServiceName AppExit Default Restart

# Environment variables injection (paths only; no credential values).
$serviceEnvironment = @(
    "USERPROFILE=$UserProfile",
    "LOCALAPPDATA=$LocalAppData",
    "APPDATA=$AppData",
    "CODEX_HOME=$(Join-Path $UserProfile '.codex')",
    "PYTHONUNBUFFERED=1",
    "MNE_BRAIN_PORT=$Port"
)
if ($CodexPath) { $serviceEnvironment += "MNE_BRAIN_CODEX_BINARY=$CodexPath" }
if ($OpenCodePath) { $serviceEnvironment += "MNE_BRAIN_OPENCODE_BINARY=$OpenCodePath" }
& $NssmPath set $ServiceName AppEnvironmentExtra @serviceEnvironment

# 9. Start Service
Write-Host "[*] Starting service '$ServiceName'..." -ForegroundColor Cyan
Start-Service -Name $ServiceName

# 10. Verify Service & Health Endpoint
Write-Host "[*] Verifying service startup and listener on port $Port..." -ForegroundColor Cyan
$verified = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 1
    $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
    if ($conn) {
        $verified = $true
        break
    }
}

if ($verified) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host " [SUCCESS] $DisplayName is running as a Windows Service!" -ForegroundColor Green
    Write-Host " Service Name: $ServiceName" -ForegroundColor Green
    Write-Host " Port:         http://127.0.0.1:$Port" -ForegroundColor Green
    Write-Host " Stdout Log:   $StdoutLog" -ForegroundColor Green
    Write-Host " Stderr Log:   $StderrLog" -ForegroundColor Green
    Write-Host " Startup Type: Automatic (Always running 24/7)" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Useful commands:" -ForegroundColor Yellow
    Write-Host "  Check Status:  .\scripts\manage_server_service.ps1 status"
    Write-Host "  View Logs:     .\scripts\manage_server_service.ps1 logs"
    Write-Host "  Restart:       .\scripts\manage_server_service.ps1 restart"
    Write-Host "  Stop:          .\scripts\manage_server_service.ps1 stop"
    Write-Host "  Uninstall:     .\scripts\manage_server_service.ps1 uninstall"
    Write-Host ""
} else {
    Write-Warning "Service was started, but port $Port is not listening yet. Check $StderrLog for details."
}
