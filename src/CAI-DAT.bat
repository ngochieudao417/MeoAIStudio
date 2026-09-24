@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo  CAI DAT MOI TRUONG - chi can chay 1 lan
echo ============================================
echo.
echo [1/4] Kiem tra va cai uv (trinh quan ly Python)...
python -m uv --version >nul 2>nul
if errorlevel 1 (
    python -m pip install uv
)
echo.
:: 07/08/2026 — DO GPU NGAY TU DAU roi cai DUNG mot ban.
:: TRUOC DAY: chay `uv sync` TRAN o day (keo onnxruntime CPU) roi buoc [4/4] moi `--extra gpu` de len
:: => may GPU bi cai CPU truoc roi de GPU: chinh la NHIP LAT sinh ra loi 'onnxruntime hong nua voi'.
:: Nay hai extra loai tru nhau (xem [tool.uv] conflicts trong pyproject) nen PHAI chon dung mot.
echo [2/4] Cai Python 3.11 + thu vien cho MediaCrawler (co the mat vai phut)...
cd MediaCrawler
:: LUOI 2 (10/08/2026): `where nvidia-smi` truot KHONG co nghia la may khong co card — driver chua cai /
:: hong / ban OEM khong kem CLI deu lam no truot. Hoi them Windows qua Win32_VideoController.
:: Doan `cpu` cho may CO card la hong NANG va KHONG tu khoi (onnxruntime ban CPU nam lai trong venv);
:: doan `gpu` cho may thieu driver chi hong NHE (ORT lang le chay CPU) va TU KHOI khi cai driver.
:: Cung luat voi desktop/setup.js va cai_gpu.card_nvidia_theo_windows - dung de lech nhau.
:: KHONG dung khoi ngoac + `!bien!` o day: file nay khong bat `enabledelayedexpansion`, ma bat len co the
:: pha cac dong khac co dau `!`. Dung `goto` de moi lenh nam tren MOT dong rieng -> `%bien%` no binh thuong.
set VC_NVIDIA=0
where nvidia-smi >nul 2>nul
if %errorlevel%==0 set VC_NVIDIA=1
if "%VC_NVIDIA%"=="1" goto :vc_xong_do
for /f "delims=" %%G in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "if ((Get-CimInstance Win32_VideoController).Name -match 'NVIDIA') { 1 } else { 0 }" 2^>nul') do set VC_NVIDIA=%%G
if "%VC_NVIDIA%"=="1" echo   Thay card NVIDIA nhung nvidia-smi khong chay - nhieu kha nang CHUA CAI DRIVER.
:vc_xong_do
if "%VC_NVIDIA%"=="1" (
    echo   Thay GPU NVIDIA - cai ban GPU ^(kem CUDA ~1.3GB, OCR/Whisper nhanh 5-10x^)...
    python -m uv sync --extra gpu
) else (
    echo   Khong thay GPU NVIDIA - cai ban CPU.
    python -m uv sync --extra cpu
)
echo.
echo [3/4] Cai trinh duyet Chromium cho Playwright...
python -m uv run playwright install chromium
echo.
:: Buoc nay TRUOC DAY chay `uv sync --extra gpu` lan hai (nhip lat). Nay buoc [2/4] da cai dung ban roi,
:: nen o day CHI KIEM CHUNG - va kiem bang cach NAP THAT, khong tin dong log 'da cai'.
echo [4/4] Kiem chung moi truong...
python -m uv run python -c "import onnxruntime as o; f=getattr(o,'__file__',None); print('   onnxruntime', o.__version__, o.get_available_providers()[:2]) if f else exit(1)"
if errorlevel 1 (
    echo   [CANH BAO] onnxruntime chua nap duoc - OCR se khong chay.
    echo   Chay lai file nay, hoac chay: python cai_gpu.py
)
echo.
echo ============================================
echo  CAI DAT XONG! Chay file CAO-VIDEO.bat de bat dau cao video.
echo ============================================
pause
