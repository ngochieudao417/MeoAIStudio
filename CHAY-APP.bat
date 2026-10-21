@echo off
title Local Studio - Video Automation App
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo   KHOI CHAY LOCAL STUDIO APP
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [LOI] Khong tim thay moi truong Virtualenv .venv!
    pause
    exit /b 1
)

echo [1/2] Dang khoi dong Web Server ngam tren port 8770...
start /b "" ".venv\Scripts\python.exe" "local_server.py"

echo [2/2] Dang mo giao dien Dashboard...
timeout /t 3 /nobreak >nul

where msedge >nul 2>&1
if %errorlevel% equ 0 (
    start "" msedge --app=http://127.0.0.1:8770/
    goto END
)

where chrome >nul 2>&1
if %errorlevel% equ 0 (
    start "" chrome --app=http://127.0.0.1:8770/
    goto END
)

start http://127.0.0.1:8770/

:END
echo.
echo [THANH CONG] Ung dung dang chay tai http://127.0.0.1:8770/
echo.
