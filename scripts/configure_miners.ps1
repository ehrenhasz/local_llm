# configure_miners.ps1
#
# This script configures the miners for local_llm.
#
# PLEASE REPLACE THE PLACEHOLDER VALUES FOR $ZanoWalletAddress and $ZanoPoolAddress
# with your actual Zano wallet address and mining pool address.

# Get the directory of the script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# Change to the parent directory (local_llm)
Set-Location $ScriptDir | Split-Path -Parent

$ZanoWalletAddress = "YOUR_ZANO_WALLET_ADDRESS"
$ZanoPoolAddress = "stratum+tcp://YOUR_ZANO_POOL_ADDRESS"

# --- Configure RTX 3060 Ti ---
python main.py config-miner add --name rtx3060ti --miner-path "./bin/t-rex/t-rex.exe" --wallet $ZanoWalletAddress --pool $ZanoPoolAddress --coin zano --worker rtx3060ti-worker --device 0

# --- Configure 1080 Ti ---
python main.py config-miner add --name gtx1080ti --miner-path "./bin/t-rex/t-rex.exe" --wallet $ZanoWalletAddress --pool $ZanoPoolAddress --coin zano --worker gtx1080ti-worker --device 1

Read-Host "Miner configuration script complete. Press Enter to exit."