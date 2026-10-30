@echo off
setlocal
cd /d "%~dp0"
echo Starting My pod promax on Windows...
where py >nul 2>&1
if %errorlevel%==0 (
  set "PYTHON=py -3"
) else (
  where python >nul 2>&1
  if errorlevel 1 (
    echo Install Python 3.10+ from https://python.org/downloads/
    pause
    exit /b 1
  )
  set "PYTHON=python"
)
if not exist ".venv\Scripts\python.exe" (
  %PYTHON% -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
where ffmpeg >nul 2>&1
if errorlevel 1 echo FFmpeg not found. Install FFmpeg and reopen the terminal.
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo Startup failed. Please review the message above.
pause
exit /b 1
