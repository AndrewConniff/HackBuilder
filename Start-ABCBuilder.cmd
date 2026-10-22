@echo off
rem Start or reuse the local ABC Builder portal and open its authenticated browser page.
setlocal
python "%~dp0scripts\start_portal.py"
set "result=%errorlevel%"
if not "%result%"=="0" (
    echo.
    echo ABC Builder could not open. Review the error above.
    echo Ensure Python is installed and available on PATH.
    pause
)
exit /b %result%
