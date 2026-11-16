@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [LUNA SHIFT] Creating Python environment...
  py -3 -m venv .venv
  if errorlevel 1 (echo Python 3 is required. & pause & exit /b 1)
)
echo [LUNA SHIFT] Installing Python requirements...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (echo Python dependencies failed. & pause & exit /b 1)
echo [LUNA SHIFT] API at http://127.0.0.1:8000/api/health
echo [LUNA SHIFT] Keep this window open.
".venv\Scripts\python.exe" -m uvicorn backend.api:app --reload --host 127.0.0.1 --port 8000
pause
