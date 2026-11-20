@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3 for Windows, then run this file again.
  pause
  exit /b 1
)
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo Could not install the QR code dependency.
  pause
  exit /b 1
)
py qr_code_generator.py
