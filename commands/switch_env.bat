@echo off
REM switch_env.bat - Switch Between Development and Production Environments

echo =====================================
echo       Switch Environment Menu
echo =====================================
echo.
echo 1. Start Production Environment (NSSM)
echo 2. Start Development Environment (Flask)
echo 3. Exit
echo.
set /p choice=Choose an option [1-3]: 

if "%choice%"=="1" goto start_prod
if "%choice%"=="2" goto start_dev
if "%choice%"=="3" goto end

:start_prod
echo.
echo Stopping any running development Flask app...
taskkill /F /IM python.exe /T 2>nul

echo Starting Production Service via NSSM...
C:\Projects\NSSM\nssm.exe start FoodLogApp

echo Checking Service Status...
C:\Projects\NSSM\nssm.exe status FoodLogApp

echo Production environment started successfully.
pause
goto end

:start_dev
echo.
echo Stopping Production Service via NSSM...
C:\Projects\NSSM\nssm.exe stop FoodLogApp

echo Activating Virtual Environment...
cd C:\Projects\LoseIt
call .\venv\Scripts\activate.bat

echo Setting Environment to Development...
set ENV=dev

echo Starting Flask Development Server...
flask run --host=0.0.0.0 --port=5001 --debug

echo Development environment started successfully.
pause
goto end

:end
exit