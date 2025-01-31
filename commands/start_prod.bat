@echo off
REM start_prod.bat - Start Production Environment

echo Stopping any running development Flask app...
taskkill /F /IM python.exe /T 2>nul

echo Starting Production Service via NSSM...
C:\Projects\NSSM\nssm.exe start FoodLogApp

echo Checking Service Status...
C:\Projects\NSSM\nssm.exe status FoodLogApp

echo Production environment started successfully.
pause