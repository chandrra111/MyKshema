@echo off
rem Start the MyKshema API (default http://localhost:8000). Optional port: run-backend.cmd 8001
setlocal
set "PORT=%~1"
if "%PORT%"=="" set "PORT=8000"
cd /d "%~dp0..\backend" || exit /b 1
if not exist ".venv\Scripts\python.exe" (
  echo Creating Python virtual environment...
  python -m venv .venv || exit /b 1
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || exit /b 1
)
".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port %PORT%
