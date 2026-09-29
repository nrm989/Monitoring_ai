@echo off
REM Lancer chaque jour via Planificateur de tâches Windows
cd /d "%~dp0"
python monitor.py
if errorlevel 1 (
  echo [ALERTE] Un site est DOWN - envoi mail immediat
  python report.py --to snajnihal2002@gmail.com
) else (
  REM Rapport quotidien a 08h00 par exemple
  python report.py --to snajnihal2002@gmail.com
)
