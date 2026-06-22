@echo off
REM Build SC2Xbox.exe -- a standalone single-file Windows executable.
REM Requires the project to be installed first (install.bat).
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  echo [error] Run install.bat first.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat

echo Installing PyInstaller (if needed)...
pip install pyinstaller >nul

echo.
echo Building SC2Xbox.exe ...
echo  - bundling SDL3.dll (so users don't need PySDL3 to download it)
echo  - bundling vgamepad / ViGEm client
echo.

pyinstaller --noconfirm --onefile --windowed --name SC2Xbox ^
  --icon icon.ico ^
  --add-data "config.default.json;." ^
  --add-data "logo.png;." ^
  --add-data "icon.ico;." ^
  --collect-all sdl3 ^
  --collect-all vgamepad ^
  --hidden-import pystray._win32 ^
  --hidden-import PIL._tkinter_finder ^
  app.py

if errorlevel 1 ( echo [error] build failed & pause & exit /b 1 )

echo.
echo ============================================
echo  Built: dist\SC2Xbox.exe
echo ============================================
echo Test it:  dist\SC2Xbox.exe --list
echo.
pause
