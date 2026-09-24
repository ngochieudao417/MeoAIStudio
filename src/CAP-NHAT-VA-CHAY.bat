@echo off
chcp 65001 >nul
cd /d "%~dp0"
:: Pull code moi nhat tu Git roi mo lai ViralCrawl bang MO-WEB.bat - 1 lan bam la
:: cap nhat + chay thang ban moi nhat, khoi phai tu go lenh git.
:: Neu app dang chay (cong 8770) se TU DONG dong lai truoc khi mo ban moi de nap code
:: moi - LUU/DONG cong viec dang lam TRUOC khi bam file nay de tranh mat du lieu dang xu ly.
:: GIU FILE NAY THUAN ASCII + xuong dong CRLF - chuoi co dau / LF deu lam cmd.exe parse sai.

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
echo Dang dong ban dang chay ^(neu co^) de nap code moi...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8770 .*LISTENING"') do (
    taskkill /F /PID %%P >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo Dang mo ViralCrawl ban moi nhat...
start "" cmd /c ""%~dp0MO-WEB.bat""

echo.
echo Xong. Da cap nhat code + mo lai ViralCrawl voi ban moi nhat.
pause
