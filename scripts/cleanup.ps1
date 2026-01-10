# Cleans up temporary files.

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

Log-Message "Running temporary file cleanup..."

$TempFiles = @(
    "./temp_llm_file.tmp",
    "./temp_miner_file.tmp"
)

foreach ($file in $TempFiles) {
    if (Test-Path $file) {
        try {
            Remove-Item $file -Force
            Log-Message "Removed temporary file: $file"
        }
        catch {
            Log-Message "Error removing temporary file: $file. Error: $_" -Level "ERROR"
        }
    }
}

Log-Message "Temporary file cleanup complete."
