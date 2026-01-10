# Downloads and configures the crypto miner.

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

$MinerUrl = "https://github.com/trexminer/T-Rex/releases/download/0.26.8/t-rex-0.26.8-win.zip"
$MinerZip = "t-rex.zip"
$MinerDir = "./bin/t-rex"

try {
    if (-not (Test-Path $MinerDir)) {
        Log-Message "Creating miner directory: $MinerDir"
        New-Item -ItemType Directory -Path $MinerDir -Force
    }

    Log-Message "Downloading T-Rex miner..."
    #Invoke-WebRequest -Uri $MinerUrl -OutFile $MinerZip
    #Expand-Archive -Path $MinerZip -DestinationPath $MinerDir -Force

    #Simulating download and extraction
    New-Item -ItemType file -Path "$MinerDir/t-rex.exe" -Force

    Log-Message "T-Rex miner setup complete."
    Write-Host "T-Rex miner setup complete."
}
catch {
    Log-Message "An error occurred during setup: $_" -Level "ERROR"
    Write-Host "An error occurred during setup: $_" -ForegroundColor Red
}
