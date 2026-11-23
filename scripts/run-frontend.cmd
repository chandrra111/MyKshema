@echo off
rem Start the MyKshema web app (default http://localhost:3000). Optional port: run-frontend.cmd 3001
rem Uses npm.cmd, so it works even when PowerShell blocks .ps1 scripts.
setlocal
set "PORT=%~1"
if "%PORT%"=="" set "PORT=3000"
cd /d "%~dp0..\frontend" || exit /b 1
if not exist "node_modules" (
  echo Installing frontend dependencies...
  call npm.cmd install || exit /b 1
)
call npm.cmd run dev -- --port %PORT%
