@echo off
if "%1"=="" goto usage
if "%1"=="dev" goto dev
if "%1"=="prod" goto prod
if "%1"=="clean" goto clean
goto usage

:dev
call app.bat dev
goto end

:prod
call app.bat prod
goto end

:clean
call app.bat clean
goto end

:usage
echo Usage: make [dev^|prod^|clean]
echo.
echo Commands:
echo   dev   - Start Flask in development mode
echo   prod  - Start Flask in production mode
echo   clean - Clean Python cache files
goto end

:end 