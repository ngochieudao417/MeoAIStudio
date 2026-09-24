@echo off
chcp 65001 >nul
cd /d "%~dp0"
:: Dong goi code moi nhat thanh 1 file .zip de GUI CHO NGUOI KHAC (khong co git/code du an,
:: chi co ban ViralCrawl DA CAI) - ho chi can giai nen roi bam VA-CODE-MOI-VAO-APP.bat ben trong,
:: KHONG can git, KHONG can quyen truy cap repo.
:: GIU FILE NAY THUAN ASCII + xuong dong CRLF - chuoi co dau / LF deu lam cmd.exe parse sai.

set "OUTDIR=%~dp0GOI-CAP-NHAT-VIRALCRAWL"
set "OUTZIP=%~dp0GOI-CAP-NHAT-VIRALCRAWL.zip"

echo ============================================
echo   Dang pull code moi nhat...
echo ============================================
git pull --ff-only
if errorlevel 1 (
    echo.
    echo [LOI] Khong pull duoc code moi ^(co thay doi cuc bo chua push, hoac mat mang^).
    echo Bao lai cho dev de kiem tra, dung tu y sua git.
    pause
    exit /b 1
)

echo.
echo Dang dong goi...
if exist "%OUTDIR%" rd /s /q "%OUTDIR%"
if exist "%OUTZIP%" del /q "%OUTZIP%"
mkdir "%OUTDIR%"

:: /XF CHAY-WEB.bat = launcher OWNER-only (VC_TIER=unlimited + VC_EMBEDDED=1 + nonce RONG).
:: 07/08/2026: da DO THAT - goi phat hanh 05/08 CO chua file nay. .gitignore chan duoc git, KHONG chan
:: robocopy (no copy tu O DIA). Day la chan o DUONG SHIP; xem them buoc go chu dong trong VA-CODE-MOI-VAO-APP.bat.
robocopy "%~dp0desktop\app-src" "%OUTDIR%\app-src" /E /XF CHAY-WEB.bat /NFL /NDL /NJH /NJS >nul

:: CHOT AN TOAN: neu vi ly do nao do file van lot vao goi thi xoa han truoc khi nen.
if exist "%OUTDIR%\app-src\CHAY-WEB.bat" del /f /q "%OUTDIR%\app-src\CHAY-WEB.bat"
if exist "%OUTDIR%\app-src\CHAY-WEB.bat" (
    echo [LOI] Khong xoa duoc CHAY-WEB.bat khoi goi - DUNG dong goi de tranh phat hanh ban mo khoa.
    pause
    exit /b 1
)
copy /y "%~dp0VA-CODE-MOI-VAO-APP.bat" "%OUTDIR%\VA-CODE-MOI-VAO-APP.bat" >nul
copy /y "%~dp0find_install.ps1" "%OUTDIR%\find_install.ps1" >nul

echo Dang nen thanh file zip...
powershell -NoProfile -Command "Compress-Archive -Path '%OUTDIR%\*' -DestinationPath '%OUTZIP%' -Force"
if not exist "%OUTZIP%" (
    echo [LOI] Nen file that bai.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Xong! Da tao file:
echo   %OUTZIP%
echo ============================================
echo Gui file zip nay cho nguoi kia. Ho chi can:
echo   1. Giai nen ra 1 thu muc bat ky
echo   2. Bam VA-CODE-MOI-VAO-APP.bat ben trong ^(bam Yes o UAC^)
echo Khong can git, khong can code du an, khong can quyen truy cap repo.
pause
