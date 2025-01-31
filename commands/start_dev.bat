@echo off
REM start_dev.bat - Start Development Environment

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