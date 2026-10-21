@echo off
chcp 65001 >nul
REM Tu xin quyen admin neu chua co
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Dang xin quyen admin...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
cd /d "%~dp0"
:: --- Chon PYTHON dung (them 06/08/2026) ---------------------------------------------------
:: Ban DEV (chay tu repo) co Meowcrawler\.venv. Ban DA CAI cho khach (resources\app-src) KHONG
:: co thu muc do -> truoc day tro cung vao day nen bam file .bat nay la CHET NGAY.
:: Nay lui ve runtime venv o userData - dung cho ma CHAY-WEB.bat va desktop\main.js dang dung.
set "VCPYW=%~dp0Meowcrawler\.venv\Scripts\pythonw.exe"
if not exist "%VCPYW%" set "VCPYW=%APPDATA%\viralcrawl-desktop\runtime\venv\Scripts\pythonw.exe"
set "VCPY=%~dp0Meowcrawler\.venv\Scripts\python.exe"
if not exist "%VCPY%" set "VCPY=%APPDATA%\viralcrawl-desktop\runtime\venv\Scripts\python.exe"
:: ---------------------------------------------------------------------------------------------
echo ============================================
echo  BAT CHE DO TU DONG: render tu khoi dong cung Windows
echo ============================================
schtasks /Create /TN "ToolCaoVideoRender" /TR "\"%~dp0render_nen.bat\"" /SC ONLOGON /RL HIGHEST /F
if %errorlevel%==0 (
    echo.
    echo [OK] Da tao tac vu.
    echo.
    echo LUU Y: bo render nen nay HIEN DANG TAT - xem render_nen.bat
    echo Render tu dong bay gio nam trong giao dien web: tab Render, nut Tu dong.
    echo Tac vu vua tao chi la cho tuong lai neu bat lai render nen.
    REM 23/08/2026 — DA BO. Tac vu "ToolCaoVideoRender" o tren chay render_nen.bat, ma file do da
    REM TAT auto-render tu lau (dong goi xu_ly_video.py trong do bi comment). Dong nay la tan du:
    REM no chay xu_ly_video.py MOT LAN ngay luc bam, ap mirror/speed/color cua xu_ly_config.json —
    REM khac han mac dinh cua giao dien web (mirror TAT, speed 1.0) => cung 1 video ra 2 ket qua.
    REM Render bay gio di qua nut "Tu dong" trong tab Render cua web (hang doi rieng, xu_ly_chon.py).
) else (
    echo [LOI] Khong tao duoc tac vu.
)
echo.
pause
