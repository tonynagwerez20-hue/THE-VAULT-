@echo off
setlocal
title Stop AMIGO External Services

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$targets = Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | Where-Object { $_.CommandLine -and $_.CommandLine -like '*launch_external_services.py*' }; if (-not $targets) { Write-Host 'No AMIGO external service process found.'; exit 0 }; $targets | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('Stopped AMIGO external service PID ' + $_.ProcessId) }"

pause
