REM app.bat

@echo off
setlocal

if "%1"=="dev" (
    echo Setting up development environment...
    set FLASK_DEBUG=1
    set ENV=dev
    call .\venv\Scripts\activate.bat
    .\venv\Scripts\python.exe app.py
) else if "%1"=="prod" (
    echo Setting up production environment...
    set FLASK_DEBUG=0
    set ENV=production
    call .\venv\Scripts\activate.bat
    .\venv\Scripts\python.exe app.py
) else if "%1"=="clean" (
    echo Cleaning Python cache files...
    for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s/q "%%d"
    del /s /q *.pyc
) else (
    echo Usage: app.bat [dev^|prod^|clean]
    exit /b 1
)

endlocal 