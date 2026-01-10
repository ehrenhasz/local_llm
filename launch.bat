@echo OFF
echo Checking Google Cloud authentication status...
gcloud auth list > NUL 2>&1
IF ERRORLEVEL 1 (
    echo You are not logged in to gcloud. Please run 'gcloud auth application-default login' in your terminal and try again.
    pause
    exit /b
)
echo Authentication found. Launching application...
start "" "dist\local_llm_gui\local_llm_gui.exe"
