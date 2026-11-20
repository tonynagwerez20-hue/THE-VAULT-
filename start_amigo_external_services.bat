@echo off
setlocal
title AMIGO External Services

set "ALGOMIND_ROOT=%~dp0"
set "PYTHON=C:\Users\USER\AppData\Local\Programs\Python\Python312\python.exe"
set "MT5_FILES=C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files"

if not exist "%PYTHON%" (
  echo Python 3.12 was not found at:
  echo %PYTHON%
  pause
  exit /b 1
)
if not exist "%MT5_FILES%" (
  echo MT5 Files folder was not found:
  echo %MT5_FILES%
  pause
  exit /b 1
)

echo Starting AMIGO external context services.
echo CFTC/news context will be written to:
echo %MT5_FILES%\Amigo_ext_in.txt
echo Close this window or press Ctrl+C to stop the service.
"%PYTHON%" -B "%ALGOMIND_ROOT%Python\launch_external_services.py" --files "%MT5_FILES%"
echo.
echo AMIGO external services stopped. Exit code: %ERRORLEVEL%
pause
