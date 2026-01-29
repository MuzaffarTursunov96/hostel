@echo off
echo === Building HostelManager EXE ===

call venv\Scripts\activate.bat

python -m PyInstaller ^
  --clean ^
  --noconfirm ^
  --name HostelManager ^
  --windowed ^
  --onefile ^
  --icon=assets\app1.ico ^
  --add-data "assets;assets" ^
  --add-data "style.qss;." ^
  --add-data ".env;." ^
  --collect-all PySide6 ^
  --collect-all shiboken6 ^
  main_qt.py

echo.
echo === BUILD FINISHED ===
pause
