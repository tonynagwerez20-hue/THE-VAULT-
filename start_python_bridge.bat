@echo off
REM AlgoMind Python External Service Starter
SET MQL5_FILES=C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files
SET PYTHON_DIR=C:\Users\USER\Desktop\algomind\Python

cd /d "%PYTHON_DIR%"
set PYTHONPATH=%PYTHON_DIR%

echo Starting AlgoMind External Service...
echo Market Snapshot path: %MQL5_FILES%\algomind_mkt_out.txt
echo External Context path: %MQL5_FILES%\algomind_ext_in.txt

python run_external_service.py --mkt "%MQL5_FILES%\algomind_mkt_out.txt" --out "%MQL5_FILES%\algomind_ext_in.txt" --interval 5.0
pause
