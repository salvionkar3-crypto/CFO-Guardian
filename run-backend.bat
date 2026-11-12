@echo off
echo ===================================================
echo Starting Guardian CFO - FastAPI Backend Server
echo ===================================================
cd /d "%~dp0backend"
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please run:
    echo   python -m venv backend\venv
    echo   backend\venv\Scripts\pip install -r backend\requirements.txt
    pause
    exit /b 1
)
set PYTHONPATH=%cd%
echo [INFO] Binding Guardian CFO FastAPI server on http://127.0.0.1:8000 (0.0.0.0)
venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

