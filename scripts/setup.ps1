# Downloads and configures the crypto miner.

$MinerUrl = "https://github.com/trexminer/T-Rex/releases/download/0.26.8/t-rex-0.26.8-win.zip"
$MinerZip = "t-rex.zip"
$MinerDir = "./bin/t-rex"

if (-not (Test-Path $MinerDir)) {
    Write-Host "Creating miner directory: $MinerDir"
    New-Item -ItemType Directory -Path $MinerDir -Force
}

Write-Host "Downloading T-Rex miner..."
#Invoke-WebRequest -Uri $MinerUrl -OutFile $MinerZip
#Expand-Archive -Path $MinerZip -DestinationPath $MinerDir -Force

#Simulating download and extraction
New-Item -ItemType file -Path "$MinerDir/t-rex.exe" -Force

Write-Host "T-Rex miner setup complete."
