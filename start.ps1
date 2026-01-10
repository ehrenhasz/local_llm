# Main startup script

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

Log-Message "Application started."

# Run cleanup script
./scripts/cleanup.ps1

# Execute the Python CLI application
Log-Message "Executing Python CLI application: main.py"
python main.py
Log-Message "Python CLI application exited."
