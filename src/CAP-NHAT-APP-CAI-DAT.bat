@echo off
chcp 65001 >nul
cd /d "%~dp0"
:: Pull code moi nhat roi VA THANG vao ban ViralCrawl DA CAI - TU DONG DO ra ban cai o dau (KHONG
:: con hardcode C:\Program Files\ViralCrawl - vi tri cai MAC DINH thuc te la
:: %LOCALAPPDATA%\Programs\ViralCrawl, nguoi dung co the tu chon noi khac luc cai dat).
:: Dung cho may dang chay ban da cai san, KHONG phai ban dev chay tu MO-WEB.bat (do dung
:: CAP-NHAT-VA-CHAY.bat).
:: Se DONG app dang chay, ghi de code, roi MO LAI app. CHI xin quyen Admin NEU thuc su can (kiem
:: tra QUYEN GHI THAT truoc, chua dong app neu chua chac chan can Admin).
:: LUU/DONG cong viec dang lam TRUOC khi bam file nay - app se bi dong cuong buc de nap code moi.
:: GIU FILE NAY THUAN ASCII + xuong dong CRLF - chuoi co dau / LF deu lam cmd.exe parse sai.

set "SRCDIR=%~dp0desktop\app-src"

:: Chi pull khi day la LAN CHAY DAU (khong phai lan chay lai sau khi xin quyen Admin - xem /elevated
:: ben duoi) - tranh pull 2 lan vo ich.
if not "%~1"=="/elevated" (
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
)

:: 1) TU DONG DO ban cai o dau - thu cac vi tri hay gap TRUOC (nhanh, khong can PowerShell).
set "APPDIR="
if exist "%LOCALAPPDATA%\Programs\ViralCrawl\ViralCrawl.exe" set "APPDIR=%LOCALAPPDATA%\Programs\ViralCrawl"
if not defined APPDIR if exist "C:\Program Files\ViralCrawl\ViralCrawl.exe" set "APPDIR=C:\Program Files\ViralCrawl"
if not defined APPDIR if exist "C:\Program Files (x86)\ViralCrawl\ViralCrawl.exe" set "APPDIR=C:\Program Files (x86)\ViralCrawl"

:: Khong thay o vi tri quen thuoc -> doc registry Uninstall.
if not defined APPDIR (
    if exist "%~dp0find_install.ps1" (
        echo Dang do tim ban cai qua registry Windows...
        for /f "usebackq delims=" %%A in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0find_install.ps1"`) do set "APPDIR=%%A"
    )
)

if not defined APPDIR (
    echo.
    echo [LOI] Khong tu dong tim thay ban cai ViralCrawl tren may nay.
    echo Bao lai de sua duong dan trong file nay.
    pause
    exit /b 1
)
if not exist "%APPDIR%\ViralCrawl.exe" (
    echo [LOI] Tim thay duong dan "%APPDIR%" nhung khong co ViralCrawl.exe trong do.
    echo Bao lai de sua duong dan trong file nay.
    pause
    exit /b 1
)
echo Tim thay ban cai o: %APPDIR%

set "DSTDIR=%APPDIR%\resources\app-src"

:: 2) KIEM TRA QUYEN GHI THAT (ghi thu 1 file roi xoa) TRUOC KHI dong app - KHONG dua vao ma loi
:: robocopy: DA DO THAT robocopy tra ve errorlevel=0 (khong phai 16) khi thu muc dich KHONG TRUY
:: CAP DUOC ma khong copy duoc file nao ("ERROR: RETRY LIMIT EXCEEDED" nhung van errorlevel 0).
set "PROBEFILE=%DSTDIR%\.vc_ghithu_probe.tmp"
set "CANGHI=0"
echo probe >"%PROBEFILE%" 2>nul
if exist "%PROBEFILE%" (
    set "CANGHI=1"
    del /q "%PROBEFILE%" >nul 2>&1
)

if "%CANGHI%"=="0" (
    :: %1 = "/elevated" khi day la lan CHAY LAI SAU KHI DA xin quyen Admin - co danh dau nay de
    :: KHONG lap vo han xin quyen (vd file bi khoa boi chuong trinh khac, du Admin cung khong ghi duoc).
    if "%~1"=="/elevated" (
        echo.
        echo [LOI] Khong ghi duoc vao "%DSTDIR%" du DA xin quyen Admin.
        echo Co the file dang bi khoa boi chuong trinh khac, hoac quyen thu muc bi chinh sach chan.
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
:: Thieu 4 file nay => moi lan cap nhat la khach mat noi luu video / watermark / provider AI / danh sach trang.
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

:: 3) CAI/BU GPU (onnxruntime-gpu + torch CUDA) NGAY TAI DAY, TRUOC KHI mo app - giong het buoc
:: setup.js lam cho ban cai MOI (xem ghi chu day du trong VA-CODE-MOI-VAO-APP.bat). May khong co
:: GPU NVIDIA thi cai_gpu.py tu bo qua het, khong ton thoi gian.
set "VENVPY=%APPDATA%\viralcrawl-desktop\runtime\venv\Scripts\python.exe"
if exist "%VENVPY%" if exist "%DSTDIR%\cai_gpu.py" (
    echo.
    echo Dang kiem tra/cap nhat tang toc GPU ^(chi mat thoi gian neu may co GPU NVIDIA VA chua co san^)...
    pushd "%APPDIR%"
    "%VENVPY%" "%DSTDIR%\cai_gpu.py"
    popd
)

echo.
echo Dang mo lai ViralCrawl...
start "" "%APPDIR%\ViralCrawl.exe"

echo.
echo Xong. Da va code moi nhat thang vao ban ViralCrawl da cai (%APPDIR%) va mo lai.
pause
