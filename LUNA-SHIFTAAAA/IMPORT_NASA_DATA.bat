@echo off
setlocal
cd /d "%~dp0"
if not exist "lunar landing.zip" (
  echo ERROR: Place your original "lunar landing.zip" in this folder.
  pause
  exit /b 1
)
py -3 tools\import_nasa_assets.py "lunar landing.zip"
if errorlevel 1 (echo NASA data import failed. & pause & exit /b 1)
pause
