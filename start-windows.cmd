@echo off
rem mentor-lab studio server - http://localhost:8771 (port can be given: start-windows.cmd 8772)
rem -X utf8: Korean prompts and logs break under the default Windows encoding (cp949)
cd /d "%~dp0"
set PORT=%~1
if "%PORT%"=="" set PORT=8771
rem same choice as setup-windows.ps1: py -3 only when it is 3.10+, otherwise python (Pillow was installed there)
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>nul
if %errorlevel%==0 (
  py -3 -X utf8 -I scripts\studio_server.py %PORT%
) else (
  python -X utf8 -I scripts\studio_server.py %PORT%
)
rem keep the window open when it stops with an error (double-click would close it at once)
if errorlevel 1 pause
