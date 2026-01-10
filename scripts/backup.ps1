# Creates a backup of the config.json file.

# --- Logging Setup ---
$LogFile = "./local_llm.log"
function Log-Message {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$Timestamp] [$Level] - $Message" | Out-File -FilePath $LogFile -Append
}

try {
    $Timestamp = Get-Date -Format "yyyyMMddHHmmss"
    $BackupFile = "config.json.$Timestamp.bak"

    Log-Message "Backing up config.json to $BackupFile"
    Write-Host "Backing up config.json to $BackupFile"
    Copy-Item -Path ./config.json -Destination $BackupFile
    Log-Message "Backup complete."
    Write-Host "Backup complete."
}
catch {
    Log-Message "An error occurred during backup: $_" -Level "ERROR"
    Write-Host "An error occurred during backup: $_" -ForegroundColor Red
}
