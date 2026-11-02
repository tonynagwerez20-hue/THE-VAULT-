@echo off
REM Amigo Master Python Services Starter (External Context + MGLE Layer)
SET MQL5_FILES=C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files
SET MQL5_FILES_B=C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\B54FD4362E205B20F698D85C43C4639C\MQL5\Files
SET PYTHON_DIR=C:\Users\USER\Desktop\Amigo\Python

cd /d "%PYTHON_DIR%"
set PYTHONPATH=%PYTHON_DIR%

echo Starting Amigo External Context Service (Dual Terminals)...
start "Amigo External Service" cmd /k "set PYTHONPATH=%PYTHON_DIR% && python run_external_service.py --mkt "%MQL5_FILES%\Amigo_mkt_out.txt" --out "%MQL5_FILES%\Amigo_ext_in.txt" --out2 "%MQL5_FILES_B%\Amigo_ext_in.txt" --interval 5.0"

echo Starting Amigo MGLE Service (Shadow Mode - Dual Terminals)...
start "Amigo MGLE Service" cmd /k "set PYTHONPATH=%PYTHON_DIR% && python run_mgle_service.py --mkt "%MQL5_FILES%\Amigo_mkt_out.txt" --out "%MQL5_FILES%\Amigo_mgle_in.txt" --out2 "%MQL5_FILES_B%\Amigo_mgle_in.txt" --interval 5.0"

echo.
echo Both Amigo Python Services launched successfully!
pause

