@echo off
echo ===================================================
echo Starting Guardian CFO (Backend + Frontend)
echo ===================================================
cd /d "%~dp0"

echo [1/2] Launching Backend on http://localhost:8000 ...
start "Guardian CFO Backend" cmd /k "run-backend.bat"

echo [2/2] Launching Frontend on http://localhost:3000 ...
start "Guardian CFO Frontend" cmd /k "run-frontend.bat"

echo.
echo ===================================================
echo Guardian CFO is starting up!
echo   * Web App:   http://localhost:3000
echo   * API Docs:  http://localhost:8000/api/v1/docs
echo   * Health:    http://localhost:8000/api/v1/health
echo ===================================================

