@echo off
rem Starts the BSG Hoarding app and opens it in the browser (README, "Demo"). Close this window to stop the app.
rem The first time it makes .venv here and installs requirements.txt. The app serves this PC only (127.0.0.1).
cd /d "%~dp0"
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo First start: making .venv and installing requirements.txt ...
  python -m venv .venv || goto :fail
  "%PY%" -m pip install -r requirements.txt || goto :fail
)
set "URL=http://127.0.0.1:8000"
for /f "delims=" %%u in ('%PY% -c "from app import settings as S; print(S.load().url)" 2^>nul') do set "URL=%%u"
"%PY%" -m app --check || echo Some checks failed: see above, or the Health page at %URL%/health
rem open the browser once the server had a few seconds to start
start "" /b cmd /c "ping -n 4 127.0.0.1 >nul & start "" %URL%"
"%PY%" -m app
exit /b %ERRORLEVEL%
:fail
echo Could not set up .venv. Is Python 3.11 or later installed and on the PATH?
pause
exit /b 1
