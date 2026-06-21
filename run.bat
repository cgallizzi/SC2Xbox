@echo off
REM Steam Controller Bridge - launcher. Passes all args through to the bridge.
REM Examples:  run.bat            run.bat --probe            run.bat --mode ds4
setlocal
cd /d "%~dp0"

echo ============================================
echo  Steam Controller Bridge
echo ============================================
echo.

if not exist ".venv\Scripts\activate.bat" (
  echo [error] Not installed yet. Double-click install.bat first, then try again.
  echo.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat

echo Starting bridge... ^(this window must stay open while you play^)
echo If it exits immediately, read the message below.
echo.

REM -u = unbuffered, so status messages appear immediately.
python -u -m src.bridge %*
set EXITCODE=%ERRORLEVEL%

echo.
echo ============================================
if "%EXITCODE%"=="0" (
  echo  Bridge stopped normally.
) else (
  echo  Bridge exited with an error ^(code %EXITCODE%^). See messages above.
)
echo ============================================
echo.
echo This window stayed open so you can read the output.
echo Close it, or press a key to exit.
pause >nul
