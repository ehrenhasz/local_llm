# Main startup script

function Show-Menu {
    Clear-Host
    Write-Host "=================================="
    Write-Host "   local_llm Controller"
    Write-Host "=================================="
    Write-Host "1. AI Mode"
    Write-Host "2. Crypto Mode"
    Write-Host "Q. Quit"
}

while ($true) {
    Show-Menu
    $selection = Read-Host "Please make a selection"

    switch ($selection) {
        "1" { 
            ./scripts/start_llm.ps1 
            Read-Host "Press Enter to continue..."
        }
        "2" { 
            ./scripts/start_miner.ps1 
            Read-Host "Press Enter to continue..."
        }
        "q" { return }
    }
}
