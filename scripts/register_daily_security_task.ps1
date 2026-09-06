# PowerShell Script to register the Daily 07:00 AM Security Review Agent Task in Windows Task Scheduler
# Run this in PowerShell as Administrator

$TaskName = "MNE_Daily_Security_Review_Agent"
$Description = "Daily 07:00 AM Cybersecurity log review, risk correlation, and HTML+PDF report dispatch for FortiGate, F5, FMC, Sophos, AD, and Exchange."
$WorkingDirectory = "D:\projects\MNE_Brain_v2"
$PythonExe = (Get-Command python).Source

if (-not $PythonExe) {
    Write-Error "Python executable not found in PATH."
    exit 1
}

$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "-m core.security_review.daily_job" -WorkingDirectory $WorkingDirectory
$Trigger = New-ScheduledTaskTrigger -Daily -At "07:00AM"
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Write-Host "Registering Scheduled Task: $TaskName..." -ForegroundColor Cyan
Register-ScheduledTask -TaskName $TaskName -Description $Description -Action $Action -Trigger $Trigger -Settings $Settings -Force

Write-Host "Task '$TaskName' registered successfully! It will run daily at 07:00 AM." -ForegroundColor Green
Write-Host "To test run immediately: Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Yellow
