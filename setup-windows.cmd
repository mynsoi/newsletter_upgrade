@echo off
rem mentor-lab Windows setup - installs everything the studio needs (safe to re-run)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-windows.ps1" %*
if "%~1"=="" pause
