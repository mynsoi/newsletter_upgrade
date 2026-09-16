@echo off
cd /d "%~dp0"
echo.
echo   아티클 발행 도구를 시작합니다...
echo   브라우저에서 http://localhost:5001 을 열어주세요.
echo   종료하려면 이 창을 닫으세요.
echo.
start http://localhost:5001
.venv\Scripts\python.exe web\server.py
