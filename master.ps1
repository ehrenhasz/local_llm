# PowerShell Master Script for local_llm Environment

# --- GLOBAL SCRIPT VARS ---
$script:llmJob = $null

# --- VIRTUAL ENVIRONMENT ACTIVATION ---
$venvName = "venv"
$activateScript = Join-Path $PSScriptRoot "$venvName\Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Write-Error "Virtual environment not found. Please run 'install.ps1' first."
    exit 1
}
& $activateScript

# --- SCRIPT SETUP ---
# Suppress scientific notation for numbers
$FormatEnumerationLimit = -1

# --- FUNCTIONS ---

function Show-GpuMonitor {
    param(
        [Parameter(Mandatory=$true)]
        [int]$refreshRate
    )

    Write-Host "Starting GPU Monitor... (Press 'q' to quit)"

    python -c @"
import time
import pynvml
from rich.live import Live
from rich.table import Table
from rich.console import Console
from rich.progress_bar import ProgressBar

console = Console()

pynvml.nvmlInit()
device_count = pynvml.nvmlDeviceGetCount()

def generate_table() -> Table:
    table = Table(title="NVIDIA GPU Monitor", show_header=True, header_style="bold magenta")
    table.add_column("GPU ID", style="dim", width=6)
    table.add_column("Product Name", min_width=20)
    table.add_column("Util", justify="right")
    table.add_column("VRAM (GB)", justify="right")
    table.add_column("Temp (°C)", justify="right")
    table.add_column("Power (W)", justify="right")

    for i in range(device_count):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        name = pynvml.nvmlDeviceGetName(handle)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # In Watts

        used_gb = round(memory.used / (1024**3), 2)
        total_gb = round(memory.total / (1024**3), 2)
        vram_str = f"{used_gb}/{total_gb}"

        util_bar = ProgressBar(total=100, completed=util.gpu, width=10)

        table.add_row(
            str(i),
            name,
            util_bar,
            vram_str,
            f"{temp}°C",
            f"{power:.1f}W"
        )
    return table

with Live(generate_table(), refresh_per_second=1.0/$refreshRate) as live:
    while True:
        try:
            time.sleep($refreshRate)
            live.update(generate_table())
        except KeyboardInterrupt:
            break

pynvml.nvmlShutdown()
"@
}

function Show-Config {
    $config = Get-Content -Path "config.json" | Out-String | ConvertFrom-Json
    Write-Host "Current Configuration:"
    $config | Format-List
}

function Edit-Config {
    # Opens config.json in Notepad.exe for lightweight editing
    Write-Host "Opening config.json in Notepad.exe for editing. Save and close Notepad to continue."
    Start-Process notepad.exe "config.json" -Wait
}

function Start-LlmService {
    if ($script:llmJob -ne $null -and ($script:llmJob.State -eq 'Running' -or $script:llmJob.State -eq 'NotStarted')) {
        return
    }

    $script:llmJob = Start-Job -ScriptBlock {
        $ErrorActionPreference = "Stop"
        $PSScriptRoot = $using:PSScriptRoot
        . "$PSScriptRoot\venv\Scripts\Activate.ps1"
        python -u "$PSScriptRoot\run_llm.py"
    }

    Start-Sleep -Seconds 3
    if ($script:llmJob.HasMoreData) {
        $errors = $script:llmJob.ChildJobs[0].Error
        if ($errors.Count -gt 0) {
            Write-Host "LLM Service failed to start with an error:" -ForegroundColor Red
            $errors | ForEach-Object { $_.ToString() }
            Stop-LlmService
        }
    }
}

function Stop-LlmService {
    if ($script:llmJob) {
        Stop-Job $script:llmJob
        Remove-Job $script:llmJob -Force
        $script:llmJob = $null
    }
}

function Reset-LlmService {
    Stop-LlmService
    Start-LlmService
}

function Show-Menu {
    Clear-Host
    $status = if ($script:llmJob -ne $null -and $script:llmJob.State -eq 'Running') {
        "[green]Running[/green]"
    } else {
        "[red]Stopped[/red]"
    }

    $pythonCode = @"
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import os

console = Console()
menu_text = Text(justify='left')
status = os.getenv('LLM_STATUS_TEXT', '[yellow]Unknown[/yellow]')
menu_text.append('--- Master Control Program ---\n\n', style='bold cyan')
menu_text.append(Text.from_markup(f'LLM Service Status: {status}\n\n'))
menu_text.append('1. Monitor GPU\n')
menu_text.append('2. View Configuration\n')
menu_text.append('3. Edit Configuration\n\n')
menu_text.append('[bold]LLM Service:[/bold]\n')
menu_text.append('s. Start\n')
menu_text.append('x. Stop\n')
menu_text.append('r. Reset\n\n')
menu_text.append('q. Quit\n')

panel = Panel(menu_text, title='local_llm', border_style='green')
console.print(panel)
"@
    $env:LLM_STATUS_TEXT = $status
    python -c $pythonCode
    Remove-Item -Path "Env:LLM_STATUS_TEXT" -ErrorAction SilentlyContinue
}

# --- AUTO-START LLM SERVICE ---
Start-LlmService

# --- MAIN LOOP ---
while ($true) {
    Show-Menu
    $choice = Read-Host "Select an option"

    switch ($choice) {
        "1" {
            $config = Get-Content -Path "config.json" | Out-String | ConvertFrom-Json
            Show-GpuMonitor -refreshRate $config.gpu_monitoring_refresh_rate_seconds
        }
        "2" {
            Show-Config
            Read-Host "Press Enter to return to the menu"
        }
        "3" {
            Edit-Config
        }
        "s" {
            Start-LlmService
        }
        "x" {
            Stop-LlmService
        }
        "r" {
            Reset-LlmService
        }
        "q" {
            Stop-LlmService
            Write-Host "Exiting."
            exit
        }
        default {
            Write-Warning "Invalid option. Please try again."
            Start-Sleep -Seconds 1
        }
    }
}