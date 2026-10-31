@echo off
rem SchiriAnalyse starten: Weboberflaeche auf http://localhost:8765
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Erst einrichten: siehe README.md, Abschnitt "Einrichtung".
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m schiri serve --open
pause
