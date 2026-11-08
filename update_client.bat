@echo off
setlocal

rem Run a temporary copy so Git can replace this updater during git pull.
if /i "%~1"=="--worker" goto worker
set "REPO_DIR=%~dp0"
if "%REPO_DIR:~-1%"=="\" set "REPO_DIR=%REPO_DIR:~0,-1%"
set "WORKER=%TEMP%\vnpy-opt-update-%RANDOM%-%RANDOM%.bat"
copy /y "%~f0" "%WORKER%" >nul
if errorlevel 1 exit /b 1
start "" "%ComSpec%" /d /c ""%WORKER%" --worker "%REPO_DIR%""
exit /b 0

:worker
cd /d "%~2"
timeout /t 1 /nobreak >nul

if not exist ".git" (
    echo ERROR: Run this file from the vn.py Git checkout.
    goto failed
)

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Client virtual environment is missing. Follow the first-time install steps in docs\02_vnpy_openctp_deployment_and_client_update.md.
    goto failed
)

powershell -NoProfile -Command "$py = (Resolve-Path '.venv\Scripts\python.exe').Path; $p = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -ieq $py -and $_.CommandLine -match 'run_windows_client\.py' }; if ($p) { [Console]::Error.WriteLine('Close the running Windows Trader window, then run this updater again.'); exit 2 }; exit 0"
if errorlevel 1 goto failed

for /f "delims=" %%B in ('git rev-parse --abbrev-ref HEAD') do set "CURRENT_BRANCH=%%B"
if /i not "%CURRENT_BRANCH%"=="master" (
    echo ERROR: Expected branch master, found %CURRENT_BRANCH%.
    goto failed
)

for /f "delims=" %%S in ('git status --porcelain') do set "DIRTY=1"
if defined DIRTY (
    echo ERROR: Local changes detected. Commit or safely back them up before updating.
    goto failed
)

git pull --ff-only origin master
if errorlevel 1 goto failed

echo Starting the Windows RPC client.
".venv\Scripts\python.exe" "examples\client_server\run_windows_client.py"
set "RC=%errorlevel%"
del /f /q "%~f0" >nul 2>&1
exit /b %RC%

:failed
echo Update stopped. Fix the message above and run update_client.bat again.
pause
exit /b 1
