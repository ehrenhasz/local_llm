# Starts the crypto miner.

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
    Log-Message "Starting the crypto miner..."
    Write-Host "Starting the crypto miner..."

    $Config = Get-Content -Raw -Path ./config.json | ConvertFrom-Json

    $MinerPath = $Config.miner_path
    $Wallet = $Config.wallet
    $Pool = $Config.pool
    $Coin = $Config.coin
    $Worker = $Config.worker

    # Create a dummy temp file
    New-Item -ItemType File -Path "./temp_miner_file.tmp" -Force

    # This is a simulation of running the miner.
    # & $MinerPath -a $Coin -o $Pool -u $Wallet -p x -w $Worker
    Log-Message "Miner Path: $MinerPath"
    Log-Message "Wallet: $Wallet"
    Log-Message "Pool: $Pool"
    Log-Message "Coin: $Coin"
    Log-Message "Worker: $Worker"

    Log-Message "Crypto miner started."
    Write-Host "Crypto miner started."
}
catch {
    Log-Message "An error occurred while starting the crypto miner: $_" -Level "ERROR"
    Write-Host "An error occurred while starting the crypto miner: $_" -ForegroundColor Red
}
