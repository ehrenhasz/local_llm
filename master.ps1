# PowerShell Master Script for local_llm Environment

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

console = Console()

pynvml.nvmlInit()
device_count = pynvml.nvmlDeviceGetCount()

def generate_table() -> Table:
    table = Table(title="NVIDIA GPU Monitor", show_header=True, header_style="bold magenta")
    table.add_column("GPU ID", style="dim", width=6)
    table.add_column("Product Name", min_width=20)
    table.add_column("Util %", justify="right")
    table.add_column("VRAM (Used/Total) GB", justify="right")
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

        table.add_row(
            str(i),
            name,
            f"{util.gpu}%",
            vram_str,
            f"{temp}°C",
            f"{power:.1f}W"
        )
    return table

with Live(generate_table(), screen=True, refresh_per_second=1.0/$refreshRate) as live:
    while True:
        try:
            time.sleep($refreshRate)
            live.update(generate_table())
        except KeyboardInterrupt:
            break

pynvml.nvmlShutdown()
"""
}

function Show-Config {
    $config = Get-Content -Path "config.json" | Out-String | ConvertFrom-Json
    Write-Host "Current Configuration:"
    $config | Format-List
}

function Edit-Config {
    # Simple editor - opens config.json in default editor
    Write-Host "Opening config.json in your default editor..."
    Start-Process "config.json"
}

function Start-LlmService {
    Write-Host "Starting LLM Service... (Placeholder)"
    Write-Host "This function will eventually load the model specified in config.json."
    # Placeholder for loading logic
    $config = Get-Content -Path "config.json" | Out-String | ConvertFrom-Json
    Write-Host "Model to load: $($config.model_name)"
    Write-Host "Quantization: $($config.quantization)"
    Read-Host "Press Enter to return to the menu"
}

function Show-Menu {
    Clear-Host
    python -c "
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()
menu_text = Text(justify='left')
menu_text.append('--- Master Control Program ---\n\n', style='bold cyan')
menu_text.append('1. Monitor GPU\n')
menu_text.append('2. View Configuration\n')
menu_text.append('3. Edit Configuration\n')
menu_text.append('4. Start LLM Service (Placeholder)\n')
menu_text.append('q. Quit\n')

panel = Panel(menu_text, title='local_llm', border_style='green')
console.print(panel)
"
}

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
        "4" {
            Start-LlmService
        }
        "q" {
            Write-Host "Exiting."
            exit
        }
        default {
            Write-Warning "Invalid option. Please try again."
            Start-Sleep -Seconds 1
        }
    }
}
