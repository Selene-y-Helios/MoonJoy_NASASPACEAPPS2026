@echo off
setlocal
cd /d "%~dp0web"
where npm.cmd >nul 2>nul
if errorlevel 1 (echo Node.js 20+ is required. & pause & exit /b 1)
if not exist "node_modules\vite\bin\vite.js" (
  echo [LUNA SHIFT] Installing SpaceView dependencies...
  call npm.cmd ci
  if errorlevel 1 (echo npm ci failed. & pause & exit /b 1)
)
echo [LUNA SHIFT] Open http://127.0.0.1:5173
call npm.cmd run dev
pause
