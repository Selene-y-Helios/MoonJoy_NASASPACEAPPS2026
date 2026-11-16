@echo off
setlocal
cd /d "%~dp0"
echo ====================================
echo       LUNAR SPACEVIEW
echo ====================================
where npm.cmd >nul 2>&1
if errorlevel 1 (
  echo ERROR: Node.js is not installed. Install Node.js 20+ from https://nodejs.org/
  pause
  exit /b 1
)
if not exist "node_modules\vite\bin\vite.js" (
  echo Installing web dependencies...
  call npm.cmd ci
  if errorlevel 1 (echo npm installation failed. Check your internet connection. & pause & exit /b 1)
)
echo Open http://127.0.0.1:5173 in your browser.
call npm.cmd run dev
pause
