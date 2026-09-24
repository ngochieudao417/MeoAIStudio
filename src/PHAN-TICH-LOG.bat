@echo off
chcp 65001 >nul
cd /d "%~dp0"
:: PHAN TICH LOG RENDER - chi ra video nao thieu sub/long tieng va THIEU VI SAO.
:: Cach dung: bam dup file nay roi KEO-THA file log vao cua so, hoac keo-tha file log THANG vao file nay.
:: GIU FILE NAY THUAN ASCII + CRLF - chuoi co dau / LF lam cmd.exe parse sai.

set "PY=%APPDATA%\viralcrawl-desktop\runtime\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

if not "%~1"=="" (
    "%PY%" "%~dp0phan_tich_log.py" "%~1"
    echo.
    pause
    exit /b
)

echo ============================================
echo   PHAN TICH LOG RENDER
echo ============================================
echo.
echo Keo-tha file log vao day roi bam Enter
echo (bo trong + Enter = tu tim _loi_render.log cua app):
set "LOGFILE="
set /p "LOGFILE=> "
:: bo dau nhay kep neu Windows tu them khi keo-tha
set LOGFILE=%LOGFILE:"=%
echo.
if "%LOGFILE%"=="" (
    "%PY%" "%~dp0phan_tich_log.py"
) else (
    "%PY%" "%~dp0phan_tich_log.py" "%LOGFILE%"
)
echo.
pause
