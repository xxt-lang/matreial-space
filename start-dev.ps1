# Start frontend (Vite) and backend (FastAPI) dev servers together.
# Usage: run  .\start-dev.ps1  from the project root.
$root   = $PSScriptRoot
$envName     = "material-space"
$backendPort = 8000

# Locate the python interpreter inside the conda env (no conda activate needed)
$condaBase = (conda info --base) -replace "`r|`n", ""
$py = Join-Path $condaBase "envs\$envName\python.exe"

if (-not (Test-Path $py)) {
    Write-Error "conda env '$envName' python not found: $py"
    exit 1
}

# Start backend
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$root\server'; & '$py' -m uvicorn app.main:app --reload --host 127.0.0.1 --port $backendPort"
) -WindowStyle Normal

# Start frontend (project now lives in web/)
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$root\web'; npm run dev"
) -WindowStyle Normal

Write-Host ""
Write-Host "Frontend: http://localhost:5173/   (dir: web/)"
Write-Host "Backend : http://127.0.0.1:$backendPort/docs  (dir: server/, API prefix /api)"
Write-Host "Close the two popped PowerShell windows to stop the servers."
