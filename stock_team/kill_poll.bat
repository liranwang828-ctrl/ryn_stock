@echo off
echo ==========================================================
echo  🚨 FORCE TERMINATING HANGING POLL PROCESSES (WINDOWS)
echo ==========================================================
echo.
echo Scanning and killing all python processes running 'poll.py'...
powershell -Command "Get-CimInstance Win32_Process -Filter 'Name=\"python.exe\"' | Where-Object { $_.CommandLine -like '*poll.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host 'Successfully terminated poll process PID:' $_.ProcessId -ForegroundColor Green }"
echo.
echo ==========================================================
echo Done!
pause
