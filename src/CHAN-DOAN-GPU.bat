@echo off
setlocal enabledelayedexpansion
echo ============================================
echo   CHAN DOAN GPU / NVENC - ViralCrawl
echo ============================================
echo.

rem --- Tim ffmpeg cua app (vendor bundle) hoac PATH ---
set "FF="
for %%D in (
  "%PROGRAMFILES%\ViralCrawl\resources\vendor\ffmpeg\bin\ffmpeg.exe"
  "%LOCALAPPDATA%\Programs\ViralCrawl\resources\vendor\ffmpeg\bin\ffmpeg.exe"
  "%APPDATA%\viralcrawl-desktop\runtime\vendor\ffmpeg\bin\ffmpeg.exe"
  "%LOCALAPPDATA%\Programs\viralcrawl-desktop\resources\vendor\ffmpeg\bin\ffmpeg.exe"
  "%~dp0vendor\ffmpeg\bin\ffmpeg.exe"
  "%~dp0desktop\vendor\ffmpeg\bin\ffmpeg.exe"
) do (
  if exist %%~D set "FF=%%~D"
)
rem quet dong neu chua thay (app cai cho khac)
if "!FF!"=="" (
  for /f "delims=" %%F in ('dir /b /s "%PROGRAMFILES%\*ffmpeg.exe" "%LOCALAPPDATA%\Programs\*ffmpeg.exe" 2^>nul ^| findstr /i "vendor\\ffmpeg\\bin"') do set "FF=%%F"
)
if "!FF!"=="" (
  where ffmpeg >nul 2>&1 && set "FF=ffmpeg"
)
if "!FF!"=="" (
  echo [X] KHONG TIM THAY ffmpeg. App co the dung ffmpeg rieng.
  goto :GPU
)
echo [ffmpeg] !FF!
echo.

echo --- 1) GPU NVIDIA + driver ---
:GPU
where nvidia-smi >nul 2>&1
if %errorlevel%==0 (
  nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
) else (
  echo [!] Khong co nvidia-smi ^(may khong co GPU NVIDIA hoac driver chua cai^)
)
echo.

if "!FF!"=="" goto :END

echo --- 2) ffmpeg co h264_nvenc trong build? ---
"!FF!" -hide_banner -encoders 2>nul | findstr /C:"h264_nvenc" >nul
if %errorlevel%==0 (echo [OK] build co h264_nvenc) else (echo [X] build KHONG co h264_nvenc)
echo.

echo --- 3) TEST NVENC preset p4 ^(lenh app dung^) ---
"!FF!" -hide_banner -loglevel error -f lavfi -i "color=c=black:s=256x256:d=0.3" -c:v h264_nvenc -preset p4 -rc vbr -cq 28 -b:v 0 -f null - 2>nvenc_err.txt
if %errorlevel%==0 (
  echo [OK] NVENC p4 CHAY DUOC -^> ung dung se dung GPU
) else (
  echo [X] NVENC p4 FAIL. Loi:
  type nvenc_err.txt
  echo.
  echo --- 3b^) thu preset cu 'medium' ---
  "!FF!" -hide_banner -loglevel error -f lavfi -i "color=c=black:s=256x256:d=0.3" -c:v h264_nvenc -preset medium -rc vbr -cq 28 -b:v 0 -f null - 2>nvenc_err2.txt
  if !errorlevel!==0 (
    echo [OK] NVENC 'medium' CHAY DUOC -^> can ep NVENC_PRESET=medium
  ) else (
    echo [X] NVENC 'medium' cung FAIL. Loi:
    type nvenc_err2.txt
    echo   =^> May nay KHONG dung duoc NVENC ^(driver qua cu / GPU khong ho tro^) -^> render bang CPU ^(cham^).
    echo   =^> KHAC PHUC: cap nhat driver NVIDIA moi nhat tu nvidia.com
  )
)
del nvenc_err.txt nvenc_err2.txt 2>nul
echo.
echo ============================================
echo   XONG. Chup man hinh ket qua nay gui lai.
echo ============================================
:END
pause
