@echo off
setlocal
rem First-time bootstrap. py.exe is not required; an explicit path is optional.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup_windows_client.ps1" %*
exit /b %errorlevel%
