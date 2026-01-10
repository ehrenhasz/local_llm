# Stops the crypto miner and cleans up temp files.

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
    Log-Message "Stopping the crypto miner..."
    Write-Host "Stopping the crypto miner..."

    # Clean up temp files
    if (Test-Path "./temp_miner_file.tmp") {
        Log-Message "Cleaning up temporary files..."
        Write-Host "Cleaning up temporary files..."
        Remove-Item "./temp_miner_file.tmp"
    }

    Log-Message "Crypto miner stopped."
    Write-Host "Crypto miner stopped."
}
catch {
    Log-Message "An error occurred while stopping the crypto miner: $_" -Level "ERROR"
    Write-Host "An error occurred while stopping the crypto miner: $_" -ForegroundColor Red
}
