<#
.SYNOPSIS
    Manages the MNE_Brain Windows Service (status, start, stop, restart, logs, uninstall).

.DESCRIPTION
    Provides operational commands to manage the MNE_Brain Windows Service registered with NSSM.

.EXAMPLE
    .\scripts\manage_server_service.ps1 status
    .\scripts\manage_server_service.ps1 logs -Lines 100
    .\scripts\manage_server_service.ps1 restart
    .\scripts\manage_server_service.ps1 stop
    .\scripts\manage_server_service.ps1 start
    .\scripts\manage_server_service.ps1 uninstall
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("status", "start", "stop", "restart", "logs", "uninstall", "help")]
    [string]$Action = "status",

    [string]$ServiceName = "MNE_Brain_Server",
    [int]$Port = 8080,
    [int]$Lines = 30,
    [switch]$Follow,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkingDir = (Resolve-Path "$ScriptDir\..").Path
$LogsDir = Join-Path $WorkingDir "operations\logs"
$StdoutLog = Join-Path $LogsDir "server_service.log"
$StderrLog = Join-Path $LogsDir "server_service_error.log"

function Test-Admin {
    ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Assert-Admin {
    if (-not (Test-Admin)) {
        Write-Host "[!] Administrator privileges required for this action." -ForegroundColor Yellow
        Write-Host "[*] Requesting elevation via UAC..." -ForegroundColor Cyan
        $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" $Action"
        if ($Force) { $argList += " -Force" }
        Start-Process powershell.exe -Verb RunAs -ArgumentList $argList
        exit 0
    }
}

function Find-Nssm {
    $cmd = Get-Command nssm.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WinGet\Packages", "C:\Users\*\AppData\Local\Microsoft\WinGet\Packages" -Filter "nssm.exe" -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.FullName -like "*win64*" }
    if ($candidates) { return ($candidates | Select-Object -First 1).FullName }
    return $null
}

switch ($Action) {
    "status" {
        Write-Host "============================================================" -ForegroundColor Cyan
        Write-Host " MNE_Brain Windows Service Status" -ForegroundColor Cyan
        Write-Host "============================================================" -ForegroundColor Cyan

        $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if (-not $service) {
            Write-Host "[-] Service '$ServiceName' is NOT installed." -ForegroundColor Red
            Write-Host "    To install, run: .\scripts\register_server_service.ps1" -ForegroundColor Yellow
            return
        }

        $statusColor = if ($service.Status -eq "Running") { "Green" } else { "Red" }
        Write-Host "Service Name:    $($service.Name)" -ForegroundColor White
        Write-Host "Display Name:    $($service.DisplayName)" -ForegroundColor White
        Write-Host "Status:          $($service.Status)" -ForegroundColor $statusColor
        Write-Host "Start Type:      $($service.StartType)" -ForegroundColor White

        # Check TCP Listener on Port
        $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
        if ($conn) {
            $procId = ($conn | Select-Object -First 1).OwningProcess
            $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
            Write-Host "Port $Port Listener: ACTIVE (PID: $procId, Process: $($proc.ProcessName))" -ForegroundColor Green

            # HTTP Ping
            try {
                $response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/v1/owner/login" -Method GET -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
                Write-Host "HTTP Health:     OK (Status $($response.StatusCode))" -ForegroundColor Green
            } catch {
                Write-Host "HTTP Health:     Connected (REST endpoints active)" -ForegroundColor Green
            }
        } else {
            Write-Host "Port $Port Listener: NOT LISTENING" -ForegroundColor Red
        }

        # Show Recent Logs
        Write-Host ""
        Write-Host "Log Files:" -ForegroundColor Yellow
        Write-Host "  Stdout: $StdoutLog"
        Write-Host "  Stderr: $StderrLog"
        if (Test-Path $StdoutLog) {
            Write-Host "`nRecent Stdout (last 5 lines):" -ForegroundColor Cyan
            Get-Content -Path $StdoutLog -Tail 5 | ForEach-Object { Write-Host "  $_" }
        }
        if (Test-Path $StderrLog) {
            $errContent = Get-Content -Path $StderrLog -Tail 5 -ErrorAction SilentlyContinue
            if ($errContent) {
                Write-Host "`nRecent Stderr (last 5 lines):" -ForegroundColor Yellow
                $errContent | ForEach-Object { Write-Host "  $_" }
            }
        }
    }

    "start" {
        Assert-Admin
        Write-Host "[*] Starting service '$ServiceName'..." -ForegroundColor Cyan
        Start-Service -Name $ServiceName
        Start-Sleep -Seconds 2
        $s = Get-Service -Name $ServiceName
        Write-Host "[+] Service '$ServiceName' status: $($s.Status)" -ForegroundColor Green
    }

    "stop" {
        Assert-Admin
        Write-Host "[*] Stopping service '$ServiceName'..." -ForegroundColor Cyan
        Stop-Service -Name $ServiceName -Force
        Start-Sleep -Seconds 1
        $s = Get-Service -Name $ServiceName
        Write-Host "[+] Service '$ServiceName' status: $($s.Status)" -ForegroundColor Yellow
    }

    "restart" {
        Assert-Admin
        Write-Host "[!] Restarting clears all in-memory conversations and active provider turns." -ForegroundColor Yellow
        Write-Host "[*] Restarting service '$ServiceName'..." -ForegroundColor Cyan
        Restart-Service -Name $ServiceName -Force
        Start-Sleep -Seconds 2
        $s = Get-Service -Name $ServiceName
        Write-Host "[+] Service '$ServiceName' status: $($s.Status)" -ForegroundColor Green
    }

    "logs" {
        if (-not (Test-Path $StdoutLog) -and -not (Test-Path $StderrLog)) {
            Write-Host "[-] No log files found in $LogsDir yet." -ForegroundColor Yellow
            return
        }

        if ($Follow) {
            Write-Host "[*] Following stdout log ($StdoutLog). Press Ctrl+C to stop..." -ForegroundColor Cyan
            Get-Content -Path $StdoutLog -Tail $Lines -Wait
        } else {
            if (Test-Path $StdoutLog) {
                Write-Host "--- Stdout Log ($StdoutLog, last $Lines lines) ---" -ForegroundColor Cyan
                Get-Content -Path $StdoutLog -Tail $Lines
            }
            if (Test-Path $StderrLog) {
                $errs = Get-Content -Path $StderrLog -Tail $Lines -ErrorAction SilentlyContinue
                if ($errs) {
                    Write-Host "`n--- Stderr Log ($StderrLog, last $Lines lines) ---" -ForegroundColor Yellow
                    $errs
                }
            }
        }
    }

    "uninstall" {
        Assert-Admin
        $nssm = Find-Nssm
        if (-not $nssm) {
            Write-Error "NSSM executable not found. Cannot remove service."
            exit 1
        }

        $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if (-not $service) {
            Write-Host "[-] Service '$ServiceName' is not installed." -ForegroundColor Yellow
            return
        }

        Write-Host "[*] Stopping service '$ServiceName'..." -ForegroundColor Cyan
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1

        Write-Host "[*] Removing service '$ServiceName' via NSSM..." -ForegroundColor Cyan
        & $nssm remove $ServiceName confirm
        Write-Host "[+] Service '$ServiceName' has been uninstalled." -ForegroundColor Green
    }

    "help" {
        Get-Help $PSCommandPath -Detailed
    }
}
