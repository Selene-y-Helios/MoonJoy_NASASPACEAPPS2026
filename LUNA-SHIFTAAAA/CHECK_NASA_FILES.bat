@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 tools\verify_github_package.py
) else (
  python tools\verify_github_package.py
)
pause
