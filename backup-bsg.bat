@echo off
rem Daily backup of the BSG Hoarding data folder (README, "Backups"). Run by the Windows scheduled task.
rem Runs from this folder; uses .venv when it exists, else the python on the PATH. Output goes to backup.log here.
cd /d "%~dp0"
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
echo ---- %DATE% %TIME% >> backup.log
"%PY%" -m app.backup >> backup.log 2>&1
exit /b %ERRORLEVEL%
