param(
    [string]$SecretPath = "C:\ProgramData\MNE_Brain\secrets\fmc-estreamer\certificate-password.dpapi"
)

$ErrorActionPreference = "Stop"

$secretDirectory = Split-Path -Parent $SecretPath
$errorPath = "C:\ProgramData\MNE_Brain\runtime\fmc-estreamer\password-setup-error.txt"

try {
    if (-not (Test-Path -LiteralPath $secretDirectory -PathType Container)) {
        throw "The protected FMC eStreamer secret directory is not available."
    }

    Add-Type -AssemblyName System.Security
    $password = Read-Host "Enter the FMC eStreamer PKCS#12 password (typing is hidden)" -AsSecureString
    if ($null -eq $password -or $password.Length -eq 0) {
        throw "No password was entered. Type the password even though the characters are hidden."
    }

    # Use Windows DPAPI directly. This avoids importing Microsoft.PowerShell.Security,
    # which can be blocked by enterprise PowerShell module policy.
    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
    $plainBytes = $null
    try {
        $plainText = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
        $plainBytes = [System.Text.Encoding]::UTF8.GetBytes($plainText)
        $protectedBytes = [System.Security.Cryptography.ProtectedData]::Protect(
            $plainBytes,
            $null,
            [System.Security.Cryptography.DataProtectionScope]::CurrentUser
        )
        $encrypted = [Convert]::ToBase64String($protectedBytes)
        [System.IO.File]::WriteAllText($SecretPath, $encrypted, [System.Text.UTF8Encoding]::new($false))
    }
    finally {
        if ($null -ne $plainBytes) {
            [Array]::Clear($plainBytes, 0, $plainBytes.Length)
        }
        $plainText = $null
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    if (-not (Test-Path -LiteralPath $SecretPath -PathType Leaf) -or (Get-Item -LiteralPath $SecretPath).Length -eq 0) {
        throw "The encrypted password file was not created."
    }

    if (Test-Path -LiteralPath $errorPath -PathType Leaf) {
        [System.IO.File]::Delete($errorPath)
    }
    Write-Host "SUCCESS: FMC eStreamer certificate password stored with Windows DPAPI for the current user." -ForegroundColor Green
    Read-Host "Press Enter to close this window"
}
catch {
    $safeError = $_.Exception.Message
    [System.IO.File]::WriteAllText($errorPath, $safeError, [System.Text.UTF8Encoding]::new($false))
    Write-Host "ERROR: $safeError" -ForegroundColor Red
    Read-Host "Press Enter to close this window"
    exit 1
}
