[CmdletBinding()]
param(
    [string]$RootPath = 'F:\MNE_Brain\runtime\fmc-estreamer',
    [string]$ActiveFileName = 'events.jsonl',
    [long]$MaxFileBytes = 524288000,
    [int]$RetentionDays = 30,
    [long]$MaxTotalBytes = 5368709120
)

$ErrorActionPreference = 'Stop'

if ($MaxFileBytes -le 0) {
    throw 'MaxFileBytes must be greater than zero.'
}
if ($RetentionDays -lt 1) {
    throw 'RetentionDays must be at least one day.'
}
if ($MaxTotalBytes -lt $MaxFileBytes) {
    throw 'MaxTotalBytes must be at least MaxFileBytes.'
}

New-Item -ItemType Directory -Path $RootPath -Force | Out-Null
$activePath = Join-Path $RootPath $ActiveFileName

# Keep the active filename stable for the eStreamer writer and move only when
# it is closed. A live writer that holds the file open is left untouched; the
# next scheduled pass will rotate it after the writer releases the handle.
if (Test-Path -LiteralPath $activePath -PathType Leaf) {
    $active = Get-Item -LiteralPath $activePath
    if ($active.Length -ge $MaxFileBytes) {
        $stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
        $archivePath = Join-Path $RootPath ("events-$stamp.jsonl")
        try {
            Move-Item -LiteralPath $activePath -Destination $archivePath -ErrorAction Stop
        }
        catch {
            Write-Warning "The active spool is currently in use; rotation will be retried later. $($_.Exception.Message)"
        }
    }
}

$cutoff = (Get-Date).ToUniversalTime().AddDays(-$RetentionDays)
$archives = @(Get-ChildItem -LiteralPath $RootPath -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like 'events-*.jsonl' })

foreach ($archive in $archives) {
    if ($archive.LastWriteTimeUtc -lt $cutoff) {
        Remove-Item -LiteralPath $archive.FullName -Force
    }
}

# Enforce a total archive budget, oldest first. The active file is never
# deleted by this maintenance script.
$archives = @(Get-ChildItem -LiteralPath $RootPath -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like 'events-*.jsonl' } |
    Sort-Object LastWriteTimeUtc)
$totalBytes = [long]0
if (Test-Path -LiteralPath $activePath -PathType Leaf) {
    $totalBytes += [long](Get-Item -LiteralPath $activePath).Length
}
$totalBytes += [long](($archives | Measure-Object -Property Length -Sum).Sum)

foreach ($archive in $archives) {
    if ($totalBytes -le $MaxTotalBytes) {
        break
    }
    $totalBytes -= [long]$archive.Length
    Remove-Item -LiteralPath $archive.FullName -Force
}

Write-Output (ConvertTo-Json -Compress -InputObject ([ordered]@{
    root_path = $RootPath
    active_path = $activePath
    max_file_bytes = $MaxFileBytes
    retention_days = $RetentionDays
    max_total_bytes = $MaxTotalBytes
    total_bytes_after_cleanup = $totalBytes
}))
