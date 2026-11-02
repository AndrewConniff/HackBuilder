@echo off
rem Start or reuse the local FBC Builder portal and open its browser page.
setlocal
if exist "%~dp0.venv\Scripts\python.exe" (
    set "VIRTUAL_ENV=%~dp0.venv"
    set "PATH=%~dp0.venv\Scripts;%PATH%"
    "%~dp0.venv\Scripts\python.exe" "%~dp0scripts\start_portal.py"
) else (
    python "%~dp0scripts\start_portal.py"
)
set "result=%errorlevel%"
if not "%result%"=="0" (
    echo.
    echo FBC Builder could not open. Review the error above.
    echo Ensure Python is installed and available on PATH.
    pause
)
exit /b %result%
