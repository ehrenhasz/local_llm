# Stops the LLM server (simulation) and cleans up temp files.

Write-Host "Stopping the LLM server..."

# Clean up temp files
if (Test-Path "./temp_llm_file.tmp") {
    Write-Host "Cleaning up temporary files..."
    Remove-Item "./temp_llm_file.tmp"
}

Write-Host "LLM server stopped."
