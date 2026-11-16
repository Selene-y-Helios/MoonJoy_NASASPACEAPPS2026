@echo off
setlocal
cd /d "%~dp0"
echo Starting the NASA science API and Daniela SpaceView in separate windows.
start "LUNA SHIFT API" cmd /k call "%~dp0START_BACKEND.bat"
start "LUNA SHIFT WEBSITE" cmd /k call "%~dp0START_WEBSITE.bat"
echo Open the Local URL shown by Vite in the WEBSITE window (5173 or 5174).
pause
