# build.ps1
# This script installs the dependencies, builds the application, and creates a distributable package.

# --- Install Dependencies ---
Write-Host "Installing dependencies from requirements.txt..."
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install dependencies. Aborting."
    exit 1
}

# --- Build the Application ---
Write-Host "Building the application with PyInstaller..."
python -m PyInstaller local_llm.spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to build the application. Aborting."
    exit 1
}

# --- Create the App Pack ---
Write-Host "Creating the application package..."
$AppName = "local_llm"
# TODO: Get version from a centralized place
$AppVersion = "1.0"
$DistDir = "./dist"
$OutputDir = "./build_output"
$ZipFile = "$OutputDir/${AppName}_${AppVersion}.zip"

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir
}

if (Test-Path $ZipFile) {
    Remove-Item $ZipFile
}

Start-Sleep -Seconds 5

Compress-Archive -Path "$DistDir/*" -DestinationPath $ZipFile

Write-Host "Application package created at $ZipFile"
