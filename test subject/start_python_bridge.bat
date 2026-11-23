@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" -B "%~dp0Python\launch_external_services.py" %*
  goto finished
)
py -3 -c "import sys; sys.exit(0 if sys.version_info.major == 3 else 1)" >nul 2>nul
if not errorlevel 1 (
  py -3 -B "%~dp0Python\launch_external_services.py" %*
  goto finished
)
python -c "import sys; sys.exit(0 if sys.version_info.major == 3 else 1)" >nul 2>nul
if not errorlevel 1 (
  python -B "%~dp0Python\launch_external_services.py" %*
  goto finished
)
echo ERROR: Python 3 was not found. Install/configure Python before starting AMIGO services.
exit /b 1
:finished
set "AMIGO_EXIT=%ERRORLEVEL%"
if not "%AMIGO_EXIT%"=="0" echo AMIGO service stopped with error %AMIGO_EXIT%. Read the diagnostic above.
if "%~1"=="" pause
exit /b %AMIGO_EXIT%
