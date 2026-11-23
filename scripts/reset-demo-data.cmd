@echo off
rem Restore the synthetic demo dataset (wipes local JSON data and uploads)
cd /d "%~dp0..\backend" || exit /b 1
".venv\Scripts\python.exe" -m scripts.reset_demo_data
