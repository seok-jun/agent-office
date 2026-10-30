@echo off
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\pythonw.exe" (
  start "Agent Office" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0app.py"
  exit /b
)
python app.py
if errorlevel 1 pause
