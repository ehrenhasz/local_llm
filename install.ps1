# PowerShell Installation Script for local_llm Environment
# Target System: Windows with NVIDIA RTX 3060

# --- CONFIGURATION ---
$pythonVersion = "3.10"
$cudaVersion = "12.1" # Recommended for RTX 30-series and PyTorch
$venvName = "venv"

# --- HELPER FUNCTIONS ---
function Test-CommandExists {
    param($command)
    return (Get-Command $command -ErrorAction SilentlyContinue)
}

function Write-Separator {
    Write-Host "--------------------------------------------------"
}

# --- SCRIPT START ---
Write-Host "Starting setup for the local_llm environment..."
Write-Separator

# 1. PREREQUISITE CHECKS
Write-Host "Step 1: Checking for prerequisites..."

if (-not (Test-CommandExists "git")) {
    Write-Error "Git is not found. Please install Git and ensure it's in your PATH."
    exit 1
}

if (-not (Test-CommandExists "python")) {
    Write-Error "Python is not found. Please install Python version $pythonVersion and ensure it's in your PATH."
    # Provide direct link for convenience
    Write-Host "Download Python from: https://www.python.org/downloads/"
    exit 1
}

$pyVersionInfo = python --version
Write-Host "Found Python: $pyVersionInfo"
Write-Host "Prerequisite check passed."
Write-Separator

# 2. GPU ENVIRONMENT SETUP (NVIDIA RTX 3060)
Write-Host "Step 2: Checking for NVIDIA GPU environment..."

try {
    $nvidiaSmi = nvidia-smi
    Write-Host "NVIDIA driver detected."
    Write-Host "GPU Info:"
    $nvidiaSmi | Select-String -Pattern "Product Name"
} catch {
    Write-Error "NVIDIA driver not found or 'nvidia-smi' command failed."
    Write-Host "Please install the latest NVIDIA Game Ready or Studio driver for your RTX 3060."
    Write-Host "Download from: https://www.nvidia.com/Download/index.aspx"
    exit 1
}

# Check for CUDA Toolkit
$cudaPath = "$($env:ProgramFiles)\NVIDIA GPU Computing Toolkit\CUDA\v$cudaVersion"
if (Test-Path $cudaPath) {
    Write-Host "NVIDIA CUDA Toolkit version $cudaVersion found."
} else {
    Write-Warning "NVIDIA CUDA Toolkit version $cudaVersion not found at the expected path."
    Write-Host "The script will proceed, but PyTorch installation might fail if CUDA is not correctly installed."
    Write-Host "It is highly recommended to install CUDA Toolkit $cudaVersion for your RTX 3060."
    Write-Host "Download from: https://developer.nvidia.com/cuda-toolkit-archive"
}
Write-Host "GPU environment check complete."
Write-Separator

# 3. PYTHON VIRTUAL ENVIRONMENT
Write-Host "Step 3: Creating Python virtual environment..."
$venvPath = Join-Path $PSScriptRoot $venvName
if (Test-Path $venvPath) {
    Write-Host "Virtual environment '$venvName' already exists. Skipping creation."
} else {
    Write-Host "Creating virtual environment named '$venvName'..."
    python -m venv $venvName
    Write-Host "Virtual environment created."
}
Write-Separator

# 4. DEPENDENCY INSTALLATION
Write-Host "Step 4: Installing Python dependencies..."
Write-Host "This may take a significant amount of time, especially for PyTorch."

# Activate virtual environment for this script session
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
& $activateScript

# Create requirements.txt
$requirements = @"
--index-url https://download.pytorch.org/whl/cu121
torch
transformers
accelerate
bitsandbytes
pynvml
rich
"@
Set-Content -Path "requirements.txt" -Value $requirements

pip install -r requirements.txt

Write-Host "Dependency installation complete."
Write-Separator

# 5. INITIAL MODEL DOWNLOAD (Placeholder)
Write-Host "Step 5: Downloading initial test model..."
# This part will be handled by the master script in the future,
# but we can add a simple test here.
$modelName = "EleutherAI/gpt-neo-125M"
Write-Host "Attempting to download test model: $modelName"
# The following python command will download the model to the cache.
python -c "from transformers import AutoModel; AutoModel.from_pretrained('$modelName')"

if ($?) {
    Write-Host "Test model downloaded successfully."
} else {
    Write-Error "Failed to download the test model. There might be an issue with the internet connection or the transformers library."
}
Write-Separator

Write-Host "Installation script finished."
Write-Host "To activate the environment in your shell, run: .\$venvName\Scripts\Activate.ps1"
