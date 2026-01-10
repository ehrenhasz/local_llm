# local_llm_controller.ps1
# This script provides an interactive menu to control the local_llm application.

function Show-Menu {
    Clear-Host
    Write-Host "==========================="
    Write-Host "  Local LLM / Crypto MENU  "
    Write-Host "==========================="
    Write-Host "1: Start AI Mode"
    Write-Host "2: Start Crypto Mode"
    Write-Host "3: Stop All Miners"
    Write-Host "4: Show Dashboard"
    Write-Host "Q: Quit"
}

do {
    Show-Menu
    $input = Read-Host "Please make a selection"

    switch ($input) {
        '1' {
            Write-Host "Starting AI Mode..."
            python ../main.py ai
        }
        '2' {
            Write-Host "Starting Crypto Mode..."
            python ../main.py crypto
        }
        '3' {
            Write-Host "Stopping all miners..."
            python ../main.py stop-crypto
        }
        '4' {
            Write-Host "Starting Dashboard..."
            python ../main.py dashboard
        }
        'q' {
            Write-Host "Exiting..."
            return
        }
        default {
            Write-Host "Invalid selection. Please try again."
            Start-Sleep -Seconds 2
        }
    }
} while ($input -ne 'q')
