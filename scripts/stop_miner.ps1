# Stops the crypto miner and cleans up temp files.

Write-Host "Stopping the crypto miner..."

# Clean up temp files
if (Test-Path "./temp_miner_file.tmp") {
    Write-Host "Cleaning up temporary files..."
    Remove-Item "./temp_miner_file.tmp"
}

Write-Host "Crypto miner stopped."
