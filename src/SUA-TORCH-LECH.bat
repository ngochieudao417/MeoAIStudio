@echo off
chcp 65001 >nul
cd /d "%~dp0"
:: SUA TORCH LECH PHIEN BAN - nguyen nhan lam ASR (nghe loi thoai) CHET NATIVE, keo theo MAT SUB CA VIDEO.
::
:: Trieu chung tren log:  "ASR subprocess thoat bat thuong (ma 3221226505)"  (= 0xC0000409)
:: roi app bao sai la    "video khong co tieng noi ro hoac chu goc qua mo/dong".
::
:: Nguyen nhan THAT (do tren may chu du an 06/08/2026):
::   torch       = 2.8.0+cpu     <-- SAI (ban CPU, va sai phien ban)
::   torchaudio  = 2.5.1+cu121   <-- ban CUDA cho torch 2.5.1
::   => 2 goi KHONG tuong thich ABI -> "import torch" vo -> ctranslate2 vo theo -> ASR chet.
:: Du an GHIM phien ban torch trong Meowcrawler\pyproject.toml (hien tai 2.8.0), va cai_gpu.py
:: doc THANG con so do ra (ham _ver_torch_ghim) - MOT NGUON SU THAT.
:: 06/08/2026: script nay TRUOC DAY ghim cung 2.5.1+cu121 trong khi pyproject ghim 2.8.0
:: => chinh cai script "sua lech" lai TU TAO ra lech ABI. Nay khong ghim cung nua.
::
:: Tai ~2.3GB, chay 1 lan. PHAI DONG HAN app truoc (script tu dong lam).
:: GIU FILE NAY THUAN ASCII + CRLF.

set "VENV=%APPDATA%\viralcrawl-desktop\runtime\venv\Scripts\python.exe"
set "UV=C:\Program Files\ViralCrawl\resources\vendor\uv.exe"
if not exist "%UV%" set "UV=%LOCALAPPDATA%\Programs\ViralCrawl\resources\vendor\uv.exe"

if not exist "%VENV%" (
    echo [LOI] Khong thay venv cua app: "%VENV%"
    pause
    exit /b 1
)
if not exist "%UV%" (
    echo [LOI] Khong thay uv.exe trong thu muc cai ViralCrawl.
    pause
    exit /b 1
)

echo ============================================
echo   SUA TORCH LECH PHIEN BAN
echo ============================================
echo.
echo Truoc khi sua - phien ban hien tai:
"%VENV%" -c "import importlib.metadata as m;[print('  ',p,'=',m.version(p)) for p in ('torch','torchaudio','ctranslate2','faster-whisper','onnxruntime')]" 2>nul
echo.

echo Dang dong HAN ViralCrawl (bao gom moi tien trinh con)...
taskkill /F /IM ViralCrawl.exe /T >nul 2>&1
timeout /t 3 /nobreak >nul
taskkill /F /IM ViralCrawl.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

echo.
:: --- Tim thu muc code cua app (de goi lai cai_gpu.py, khoi viet lai logic o day) ---
set "APPSRC=C:\Program Files\ViralCrawl\resources\app-src"
if not exist "%APPSRC%\cai_gpu.py" set "APPSRC=%LOCALAPPDATA%\Programs\ViralCrawl\resources\app-src"

:: Lay DUNG so phien ban du an dang ghim. Doc qua cai_gpu._ver_torch_ghim() thay vi parse toml o
:: day - de chi co MOT cho biet su that. cai_gpu chi import os/shutil/subprocess/sys nen van
:: import duoc ngay ca khi torch dang hong.
set "TVER="
if exist "%APPSRC%\cai_gpu.py" (
    "%VENV%" -c "import sys;sys.path.insert(0,r'%APPSRC%');import cai_gpu;open(r'%TEMP%\vc_tver.txt','w').write(cai_gpu._ver_torch_ghim() or '')" 2>nul
    if exist "%TEMP%\vc_tver.txt" set /p TVER=<"%TEMP%\vc_tver.txt"
    del "%TEMP%\vc_tver.txt" >nul 2>&1
)
if "%TVER%"=="" (
    set "TVER=2.8.0"
    echo [CANH BAO] Khong doc duoc phien ban ghim tu pyproject - dung ban du phong 2.8.0.
)

:: May CO NVIDIA: giao han cho cai_gpu.py - no cai torch dung kenh CUDA (cu126 roi cu128), kem
:: cudart/cuBLAS/cuDNN cho ctranslate2, va VERIFY that sau khi cai (khong tin returncode).
where nvidia-smi >nul 2>&1
if not errorlevel 1 if exist "%APPSRC%\cai_gpu.py" (
    echo Dang cai torch %TVER% + goi CUDA qua cai_gpu.py - tai ~2.3GB, doi vai phut...
    "%VENV%" "%APPSRC%\cai_gpu.py"
    goto :da_cai
)

:: May KHONG co NVIDIA (hoac khong thay cai_gpu.py): cai ban CPU dung so ghim. Lech torch/torchaudio
:: moi la nguyen nhan lam ASR chet - khong phai chuyen may co GPU hay khong.
echo Dang cai torch %TVER% (ban CPU) - doi vai phut...
"%UV%" pip install --python "%VENV%" torch==%TVER% torchaudio==%TVER%
:da_cai
if errorlevel 1 (
    echo.
    echo [LOI] Cai that bai. Thuong do: app chua dong han ^(file .dll dang bi giu^), hoac mat mang.
    echo Dong HAN ViralCrawl tu Task Manager roi chay lai file nay.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   KIEM TRA LAI ^(quan trong - dung tin la xong^)
echo ============================================
"%VENV%" -c "import torch;print('  torch      =',torch.__version__,'| CUDA dung duoc:',torch.cuda.is_available())"
if errorlevel 1 goto :hong
"%VENV%" -c "import ctranslate2;print('  ctranslate2 = OK',ctranslate2.__version__)"
if errorlevel 1 goto :hong
"%VENV%" -c "import faster_whisper;print('  faster_whisper = OK',faster_whisper.__version__)"
if errorlevel 1 goto :hong
"%VENV%" -c "import onnxruntime;print('  onnxruntime = OK',onnxruntime.__version__)"
if errorlevel 1 goto :hong

echo.
echo ============================================
echo   XONG - ASR da nap duoc. Mo lai app va render thu.
echo ============================================
goto :mo

:hong
echo.
echo [VAN CON LOI] Mot goi van khong nap duoc - chup man hinh nay gui lai.
pause
exit /b 1

:mo
set "APPDIR=C:\Program Files\ViralCrawl"
if not exist "%APPDIR%\ViralCrawl.exe" set "APPDIR=%LOCALAPPDATA%\Programs\ViralCrawl"
if exist "%APPDIR%\ViralCrawl.exe" start "" "%APPDIR%\ViralCrawl.exe"
timeout /t 3 /nobreak >nul
