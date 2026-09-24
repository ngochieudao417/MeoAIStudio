@echo off
chcp 65001 >nul
cd /d "%~dp0"
:: VA NGAY code trong repo nay vao ban ViralCrawl DA CAI - KHONG git pull (dung khi code vua sua
:: CHUA commit/push, vd dang trong mot phien sua bug). Moi logic do ban cai / xin quyen Admin /
:: dong-mo app deu COPY NGUYEN VAN tu CAP-NHAT-APP-CAI-DAT.bat de khong lech hanh vi giua 2 file.
:: LUU/DONG cong viec dang lam TRUOC khi bam file nay - app se bi dong cuong buc de nap code moi.
:: GIU FILE NAY THUAN ASCII + xuong dong CRLF - chuoi co dau / LF deu lam cmd.exe parse sai.

set "SRCDIR=%~dp0desktop\app-src"
if not exist "%SRCDIR%" (
    echo [LOI] Khong thay thu muc "desktop\app-src" trong repo nay.
    pause
    exit /b 1
)

set "APPDIR="
if exist "%LOCALAPPDATA%\Programs\ViralCrawl\ViralCrawl.exe" set "APPDIR=%LOCALAPPDATA%\Programs\ViralCrawl"
if not defined APPDIR if exist "C:\Program Files\ViralCrawl\ViralCrawl.exe" set "APPDIR=C:\Program Files\ViralCrawl"
if not defined APPDIR if exist "C:\Program Files (x86)\ViralCrawl\ViralCrawl.exe" set "APPDIR=C:\Program Files (x86)\ViralCrawl"

if not defined APPDIR (
    if exist "%~dp0find_install.ps1" (
        echo Dang do tim ban cai qua registry Windows...
        for /f "usebackq delims=" %%A in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0find_install.ps1"`) do set "APPDIR=%%A"
    )
)

if not defined APPDIR (
    echo.
    echo [LOI] Khong tu dong tim thay ban cai ViralCrawl tren may nay.
    pause
    exit /b 1
)
if not exist "%APPDIR%\ViralCrawl.exe" (
    echo [LOI] Tim thay "%APPDIR%" nhung khong co ViralCrawl.exe trong do.
    pause
    exit /b 1
)
echo Tim thay ban cai o: %APPDIR%

set "DSTDIR=%APPDIR%\resources\app-src"

:: KIEM TRA QUYEN GHI THAT (ghi thu 1 file roi xoa) TRUOC KHI dong app - khong dua vao ma loi robocopy.
set "PROBEFILE=%DSTDIR%\.vc_ghithu_probe.tmp"
set "CANGHI=0"
echo probe >"%PROBEFILE%" 2>nul
if exist "%PROBEFILE%" (
    set "CANGHI=1"
    del /q "%PROBEFILE%" >nul 2>&1
)

if "%CANGHI%"=="0" (
    if "%~1"=="/elevated" (
        echo.
        echo [LOI] Khong ghi duoc vao "%DSTDIR%" du DA xin quyen Admin.
        echo Co the file dang bi khoa boi chuong trinh khac.
        pause
        exit /b 1
    )
    echo.
    echo Thu muc cai dat can quyen Administrator de ghi - dang xin quyen...
    echo Bam Yes o hop thoai vua hien ra roi doi mot lat.
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -ArgumentList '/elevated' -WorkingDirectory '%~dp0' -Verb RunAs"
    exit /b
)

echo.
echo Dang dong ViralCrawl dang chay...
taskkill /F /IM ViralCrawl.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

echo Dang va code moi vao ban da cai (giu nguyen cau hinh + du lieu cua ban)...
:: /XF = CHUA RA cac file CAU HINH CUA KHACH (xem chu thich day du trong VA-CODE-MOI-VAO-APP.bat).
:: Thieu 4 file nay => moi lan va code la khach mat noi luu video / watermark / provider AI / danh sach trang.
robocopy "%SRCDIR%" "%DSTDIR%" /E /XF app_config.json _login_check.json app_settings.json xu_ly_config.json ai_cau_hinh.json trang_config.json /R:2 /W:1 /NFL /NDL /NJH /NJS
if errorlevel 8 (
    echo.
    echo [LOI] Copy code that bai ^(ma loi robocopy: %errorlevel%^).
    pause
    exit /b 1
)

:: GO CHU DONG - robocopy o tren KHONG co /PURGE (co y, de khong xoa cau hinh khach) nen XOA mot file
:: khoi ban phat hanh KHONG BAO GIO toi duoc may khach da nhan. Xem giai thich day du trong
:: VA-CODE-MOI-VAO-APP.bat. CHI xoa DUNG mot ten file, khong wildcard.
if exist "%DSTDIR%\CHAY-WEB.bat" (
    del /f /q "%DSTDIR%\CHAY-WEB.bat"
    if exist "%DSTDIR%\CHAY-WEB.bat" (
        echo [CANH BAO] Khong xoa duoc CHAY-WEB.bat ^(file dang mo?^). Hay dong app roi chay lai.
    ) else (
        echo [OK] Da go launcher cu khong hop le khoi ban cai.
    )
)

echo.
echo ============================================
echo   DA VA XONG. Dang mo lai ViralCrawl...
echo ============================================
start "" "%APPDIR%\ViralCrawl.exe"
timeout /t 3 /nobreak >nul
