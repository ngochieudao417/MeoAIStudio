@echo off
REM Va cac file da sua vao APP DA CAI (C:\Program Files\ViralCrawl).
REM Tu xin quyen Administrator - Program Files khong cho ghi thuong.
REM Nguon: desktop\app-src trong repo. Co sao luu ban cu truoc khi de.
setlocal
set PS=%~dp0plans\260810-da-kenh-nguon-theodoi\scripts\va_vao_app.ps1

net session >nul 2>&1
if %errorlevel%==0 goto RUN

echo Dang xin quyen Administrator...
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b

:RUN
echo ============================================
echo  VA FILE VAO APP DA CAI
echo ============================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS%"
echo.
pause
