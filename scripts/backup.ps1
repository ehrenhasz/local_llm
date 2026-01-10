# Creates a backup of the config.json file.

$Timestamp = Get-Date -Format "yyyyMMddHHmmss"
$BackupFile = "config.json.$Timestamp.bak"

Write-Host "Backing up config.json to $BackupFile"
Copy-Item -Path ./config.json -Destination $BackupFile
