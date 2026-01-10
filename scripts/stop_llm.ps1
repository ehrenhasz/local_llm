# Stops the LLM server (simulation) and cleans up temp files.

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
    Log-Message "Stopping the LLM server..."
    Write-Host "Stopping the LLM server..."

    # Clean up temp files
    if (Test-Path "./temp_llm_file.tmp") {
        Log-Message "Cleaning up temporary files..."
        Write-Host "Cleaning up temporary files..."
        Remove-Item "./temp_llm_file.tmp"
    }

    Log-Message "LLM server stopped."
    Write-Host "LLM server stopped."
}
catch {
    Log-Message "An error occurred while stopping the LLM server: $_" -Level "ERROR"
    Write-Host "An error occurred while stopping the LLM server: $_" -ForegroundColor Red
}
