# Guardian CFO - Unified Startup Script
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "Starting Guardian CFO (Backend + Frontend)" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $rootDir

# Launch backend in separate window
Write-Host "[1/2] Launching Backend on http://127.0.0.1:8000 ..." -ForegroundColor Green
Start-Process cmd -ArgumentList "/k `"$rootDir\run-backend.bat`""

# Wait briefly for backend initialization
Start-Sleep -Seconds 2

# Launch frontend in current window
Write-Host "[2/2] Launching Frontend on http://localhost:3000 ..." -ForegroundColor Green
Write-Host "`nAccess URLs:" -ForegroundColor Yellow
Write-Host "  * Web App:   http://localhost:3000" -ForegroundColor White
Write-Host "  * API Docs:  http://127.0.0.1:8000/api/v1/docs" -ForegroundColor White
Write-Host "  * Health:    http://127.0.0.1:8000/api/v1/health`n" -ForegroundColor White

Set-Location "$rootDir\frontend"
npm.cmd run dev

