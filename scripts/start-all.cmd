@echo off
rem Open the MyKshema API and web app in two new windows, then the browser.
rem Double-click this file, or run it from Command Prompt or PowerShell.
start "MyKshema backend" cmd /k call "%~dp0run-backend.cmd"
start "MyKshema frontend" cmd /k call "%~dp0run-frontend.cmd"
echo Starting MyKshema... the app opens at http://localhost:3000 in about 15 seconds.
timeout /t 15 /nobreak >nul
start "" http://localhost:3000
