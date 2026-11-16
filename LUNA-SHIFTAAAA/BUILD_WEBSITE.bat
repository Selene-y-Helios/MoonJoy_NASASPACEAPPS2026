@echo off
setlocal
cd /d "%~dp0web"
where npm.cmd >nul 2>nul
if errorlevel 1 (echo Node.js 20+ is required. & pause & exit /b 1)
if not exist "node_modules\vite\bin\vite.js" call npm.cmd ci
call npm.cmd run build
pause
