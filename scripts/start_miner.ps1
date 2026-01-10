# Starts the crypto miner.

$Config = Get-Content -Raw -Path ./config.json | ConvertFrom-Json

$MinerPath = $Config.miner_path
$Wallet = $Config.wallet
$Pool = $Config.pool
$Coin = $Config.coin
$Worker = $Config.worker

Write-Host "Starting the crypto miner..."

# Create a dummy temp file
New-Item -ItemType File -Path "./temp_miner_file.tmp" -Force

# This is a simulation of running the miner.
# & $MinerPath -a $Coin -o $Pool -u $Wallet -p x -w $Worker

Write-Host "Crypto miner started."
