@echo off
if "%1"=="" goto usage
if "%1"=="dev" goto dev
if "%1"=="prod" goto prod
if "%1"=="clean" goto clean
goto usage

:dev
echo Setting up development environment...
python setup_env.py dev
echo Starting Flask in development mode...
python app.py
goto end

:prod
echo Setting up production environment...
python setup_env.py prod
echo Starting Flask in production mode...
python app.py
goto end

:clean
echo Cleaning up Python cache files...
del /s /q *.pyc
del /s /q __pycache__
rmdir /s /q __pycache__
goto end

:usage
echo Usage: app [dev^|prod^|clean]
echo.
echo Commands:
echo   dev   - Start Flask in development mode
echo   prod  - Start Flask in production mode
echo   clean - Clean Python cache files
goto end

:end 