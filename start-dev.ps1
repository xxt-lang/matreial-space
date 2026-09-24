# 同时启动前端(Vite)与后端(FastAPI)开发服务
# 用法: 在项目根目录执行  .\start-dev.ps1
$root   = $PSScriptRoot
$envName     = "material-space"
$backendPort = 8000

# 定位 conda 环境中 Python 解释器（避免依赖 conda activate）
$condaBase = (conda info --base) -replace "`r|`n", ""
$py = Join-Path $condaBase "envs\$envName\python.exe"

if (-not (Test-Path $py)) {
    Write-Error "未找到 conda 环境 '$envName' 的 python: $py"
    exit 1
}

# 启动后端
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$root\server'; & '$py' -m uvicorn app.main:app --reload --host 127.0.0.1 --port $backendPort"
) -WindowStyle Normal

# 启动前端
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$root'; npm run dev"
) -WindowStyle Normal

Write-Host ""
Write-Host "前端已启动: http://localhost:5173/"
Write-Host "后端已启动: http://127.0.0.1:$backendPort/docs  (API 前缀 /api)"
Write-Host "关闭两个弹出的 PowerShell 窗口即可停止服务。"
