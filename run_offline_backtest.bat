@echo off
echo ========================================================
echo   AMIGO ISOLATED OFFLINE STRATEGY TESTER RUNNER
echo ========================================================
echo.
echo Launching MetaTrader 5 Strategy Tester with isolated config:
echo Config: C:\Users\USER\Desktop\ALGOMIND\test_isolated_bt.ini
echo.
start "" "C:\Program Files\MetaTrader 5\terminal64.exe" /config:"C:\Users\USER\Desktop\ALGOMIND\test_isolated_bt.ini"
echo.
echo Terminal launched in Strategy Tester mode.
echo Output report will be generated at: C:\Users\USER\Desktop\ALGOMIND\isolated_bt_report.htm
echo.
pause