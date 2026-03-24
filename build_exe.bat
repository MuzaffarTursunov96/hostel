@echo off
echo === Building HostelManager EXE ===

echo === Stopping running EXE (if any) ===
taskkill /F /IM HostelManager.exe >nul 2>&1
taskkill /F /IM HostelManager_v2.exe >nul 2>&1

echo === Cleaning old build artifacts ===
if exist build rmdir /S /Q build
if exist dist rmdir /S /Q dist
if exist HostelManager.spec del /F /Q HostelManager.spec

call venv\Scripts\activate.bat

python -m PyInstaller ^
  --clean ^
  --noconfirm ^
  --name HostelManager ^
  --windowed ^
  --onefile ^
  --icon=assets\app_comfy.ico ^
  --add-data "assets;assets" ^
  --add-data "style.qss;." ^
  --add-data ".env;." ^
  --collect-all PySide6 ^
  --collect-all shiboken6 ^
  main_qt.py

echo.
echo === BUILD FINISHED ===
pause
