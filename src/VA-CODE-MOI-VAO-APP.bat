@echo off
chcp 65001 >nul
cd /d "%~dp0"
:: Va code moi (thu muc "app-src" nam canh file nay) vao ban ViralCrawl DA CAI - TU DONG DO ra
:: ban cai o dau (KHONG con hardcode C:\Program Files\ViralCrawl - vi tri cai MAC DINH thuc te la
:: %LOCALAPPDATA%\Programs\ViralCrawl, va nguoi dung co the tu chon noi khac luc cai dat).
:: KHONG can git, KHONG can code du an - chi can thu muc "app-src" + file find_install.ps1 di kem
:: trong goi nay la du.
:: Se DONG app dang chay, ghi de code, roi MO LAI app. CHI xin quyen Admin NEU thuc su can (ban cai
:: o vi tri mac dinh LOCALAPPDATA thi KHONG can quyen Admin) - kiem tra QUYEN GHI THAT truoc, chua
:: dong app voi vong lap nao ca neu chua chac chan can Admin.
:: LUU/DONG cong viec dang lam TRUOC khi bam file nay - app se bi dong cuong buc de nap code moi.
:: GIU FILE NAY THUAN ASCII + xuong dong CRLF - chuoi co dau / LF deu lam cmd.exe parse sai.

set "SRCDIR=%~dp0app-src"
if not exist "%SRCDIR%" (
    echo [LOI] Khong thay thu muc "app-src" canh file nay.
    echo Giai nen DAY DU goi cap nhat ra 1 thu muc roi chay lai, dung tach rieng file .bat.
    pause
    exit /b 1
)

:: 1) TU DONG DO ban cai o dau - thu cac vi tri hay gap TRUOC (nhanh, khong can PowerShell).
set "APPDIR="
if exist "%LOCALAPPDATA%\Programs\ViralCrawl\ViralCrawl.exe" set "APPDIR=%LOCALAPPDATA%\Programs\ViralCrawl"
if not defined APPDIR if exist "C:\Program Files\ViralCrawl\ViralCrawl.exe" set "APPDIR=C:\Program Files\ViralCrawl"
if not defined APPDIR if exist "C:\Program Files (x86)\ViralCrawl\ViralCrawl.exe" set "APPDIR=C:\Program Files (x86)\ViralCrawl"

:: Khong thay o vi tri quen thuoc -> doc registry Uninstall (dung cho du nguoi dung chon thu muc nao).
if not defined APPDIR (
    if exist "%~dp0find_install.ps1" (
        echo Dang do tim ban cai qua registry Windows...
        for /f "usebackq delims=" %%A in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0find_install.ps1"`) do set "APPDIR=%%A"
    )
)

if not defined APPDIR (
    echo.
    echo [LOI] Khong tu dong tim thay ban cai ViralCrawl tren may nay.
    echo Co the ten khac / chua cai / da go / thieu file find_install.ps1 trong goi nay.
    echo Bao lai cho nguoi gui de kiem tra.
    pause
    exit /b 1
)
if not exist "%APPDIR%\ViralCrawl.exe" (
    echo [LOI] Tim thay duong dan "%APPDIR%" nhung khong co ViralCrawl.exe trong do.
    echo Bao lai cho nguoi gui de kiem tra.
    pause
    exit /b 1
)
echo Tim thay ban cai o: %APPDIR%

set "DSTDIR=%APPDIR%\resources\app-src"

:: 2) KIEM TRA QUYEN GHI THAT (ghi thu 1 file roi xoa) TRUOC KHI dong app - KHONG dua vao ma loi
:: robocopy: DA DO THAT robocopy tra ve errorlevel=0 (khong phai 16) khi thu muc dich KHONG TRUY
:: CAP DUOC ma khong copy duoc file nao ("ERROR: RETRY LIMIT EXCEEDED" nhung van errorlevel 0) -
:: khong the dung ma loi robocopy de biet co can Admin hay khong trong truong hop nay.
set "PROBEFILE=%DSTDIR%\.vc_ghithu_probe.tmp"
set "CANGHI=0"
echo probe >"%PROBEFILE%" 2>nul
if exist "%PROBEFILE%" (
    set "CANGHI=1"
    del /q "%PROBEFILE%" >nul 2>&1
)

if "%CANGHI%"=="0" (
    :: %1 = "/elevated" khi day la lan CHAY LAI SAU KHI DA xin quyen Admin (xem Start-Process ben duoi) -
    :: co danh dau nay de KHONG lap vo han xin quyen (vd file bi khoa boi chuong trinh khac, du Admin
    :: cung khong ghi duoc). KHONG dung "net session" de doan da co quyen Admin chua - da do that
    :: no co the bao "co quyen" ngay ca khi tien trinh KHONG chay o muc High/elevated (kiem tra nhom,
    :: khong phai muc toan ven cua tien trinh) nen khong dang tin trong moi truong.
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
:: /XF = CHUA RA cac file CAU HINH CUA KHACH (code moi khong duoc de len).
:: BUG THAT (dot quet 06/08): truoc day chi chua 2 file, nen moi lan va code la ghi de app_settings.json cua
:: khach bang file nam san trong goi - file do dang chua duong dan MAY DEV (C:\New folder) => khach mat
:: out_dirs/data_root => "toan bo video da render bien mat" (thuc ra van con o o cu, app khong con tro toi).
:: 4 file bo sung deu la thu khach tu chinh trong app: noi luu video, watermark/nhac nen, provider AI, trang+kenh.
robocopy "%SRCDIR%" "%DSTDIR%" /E /XF app_config.json _login_check.json app_settings.json xu_ly_config.json ai_cau_hinh.json trang_config.json /R:2 /W:1 /NFL /NDL /NJH /NJS
if errorlevel 8 (
    echo.
    echo [LOI] Copy code that bai ^(ma loi robocopy: %errorlevel%^).
    pause
    exit /b 1
)

:: 2b) GO CHU DONG cac file KHONG DUOC PHEP nam tren may khach.
:: VI SAO CAN BUOC RIENG: robocopy o tren KHONG co /PURGE va /MIR (co y - de khong xoa file cau hinh cua
:: khach). He qua: XOA mot file khoi ban phat hanh KHONG BAO GIO toi duoc may khach da nhan no - thu muc
:: dich chi TICH LUY. Do that 07/08/2026: ban da cai co 23 file .bat trong khi app-src chi con 16.
:: CHAY-WEB.bat = launcher cu, can go khoi cac ban da nhan file nay.
:: Goi phat hanh 05/08 CO chua no => phai go tren may da nhan, khong chi chan ship.
:: CHI xoa DUNG mot ten file, TUYET DOI khong dung wildcard o day.
if exist "%DSTDIR%\CHAY-WEB.bat" (
    del /f /q "%DSTDIR%\CHAY-WEB.bat"
    if exist "%DSTDIR%\CHAY-WEB.bat" (
        echo [CANH BAO] Khong xoa duoc CHAY-WEB.bat ^(file dang mo?^). Hay dong app roi chay lai.
    ) else (
        echo [OK] Da go launcher cu khong hop le khoi ban cai.
    )
)

:: 3) CAI/BU GPU (onnxruntime-gpu + torch CUDA) NGAY TAI DAY, TRUOC KHI mo app - giong het buoc
:: setup.js lam cho ban cai MOI. Chay o day (khong doi app tu lam ngam sau khi mo) de: (a) khach
:: KHONG thay banner "dang tai, dung tat app" trong luc dang dung app - do thao tac linh tinh giua
:: luc dang tai; (b) mo app len la dung duoc GPU luon, khong phai cho lan render dau tien moi kich
:: hoat. Chi mat vai giay tren may DA co san GPU (tu kiem tra that, bo qua ngay); may khong co GPU
:: NVIDIA thi cai_gpu.py tu bo qua het (xem co_nvidia() trong file do), khong ton thoi gian.
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
echo Xong. Da va code moi nhat vao ViralCrawl (%APPDIR%) va mo lai.
pause
