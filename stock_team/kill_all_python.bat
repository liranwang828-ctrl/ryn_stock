@echo off
echo ==========================================================
echo  🚨 PANIC BUTTON: FORCE TERMINATING ALL PYTHON PROCESSES
echo ==========================================================
echo.
echo Terminating all python.exe tasks forcefully...
taskkill /F /IM python.exe
echo.
echo ==========================================================
echo Done! System responsiveness should be restored.
pause
