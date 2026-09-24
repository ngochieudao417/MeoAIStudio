@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
echo ==================================================
echo   SUA RENDER CHAM (thay ffmpeg 7.1 - dung NVENC GPU)
echo ==================================================
echo.
echo Loi: ffmpeg ban bundle can driver NVIDIA moi. May driver cu hon
echo nen NVENC khong chay -^> render bang CPU (cham). Script nay thay
echo ffmpeg 7.1 (chay duoc voi driver cu) -^> nhanh lai.
echo.
pause

rem === 1) DO cac vi tri vendor ffmpeg cua app ===
set "FOUND="
for %%D in (
  "%PROGRAMFILES%\ViralCrawl\resources\vendor\ffmpeg\bin"
  "%LOCALAPPDATA%\Programs\ViralCrawl\resources\vendor\ffmpeg\bin"
  "%PROGRAMFILES(X86)%\ViralCrawl\resources\vendor\ffmpeg\bin"
  "%APPDATA%\viralcrawl-desktop\runtime\vendor\ffmpeg\bin"
) do (
  if exist "%%~D\ffmpeg.exe" (
    set "FOUND=%%~D"
    echo [tim thay vendor] %%~D
  )
)
rem TU DO sau neu chua thay: quet moi ffmpeg.exe trong Program Files + Programs (resources\vendor\ffmpeg\bin)
if "!FOUND!"=="" (
  echo Dang quet o cung tim ffmpeg cua app...
  for /f "delims=" %%F in ('dir /b /s "%PROGRAMFILES%\*ffmpeg.exe" "%LOCALAPPDATA%\Programs\*ffmpeg.exe" 2^>nul ^| findstr /i "vendor\\ffmpeg\\bin"') do (
    set "FF1=%%~dpF"
    set "FOUND=!FF1:~0,-1!"
    echo [tim thay vendor] !FOUND!
  )
)
if "!FOUND!"=="" (
  echo [!] KHONG TIM THAY thu muc ffmpeg cua app.
  echo     Hay gui man hinh nay cho ben ho tro.
  goto :END
)

echo.
echo --- ffmpeg hien tai ---
"!FOUND!\ffmpeg.exe" -version 2>nul | findstr /B "ffmpeg version"
echo.

rem === 2) Tai ffmpeg 7.1 ===
echo [1/3] Dang tai ffmpeg 7.1 (~150MB, cho chut)...
set "TMP7=%TEMP%\ff71_%RANDOM%"
mkdir "%TMP7%" 2>nul
set "ZIP=%TMP7%\ff71.zip"
powershell -NoProfile -Command "try{[Net.ServicePointManager]::SecurityProtocol='Tls12';Invoke-WebRequest 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n7.1-latest-win64-gpl-7.1.zip' -OutFile '%ZIP%' -UseBasicParsing}catch{exit 1}"
if not exist "%ZIP%" (
  echo [X] Tai that bai. Kiem tra mang roi thu lai.
  goto :END
)

echo [2/3] Dang giai nen...
powershell -NoProfile -Command "Expand-Archive -LiteralPath '%ZIP%' -DestinationPath '%TMP7%' -Force"
set "NEWBIN="
for /d %%X in ("%TMP7%\ffmpeg-*") do set "NEWBIN=%%X\bin"
if not exist "!NEWBIN!\ffmpeg.exe" (
  echo [X] Giai nen loi.
  goto :END
)

rem === 3) DONG app + thay ffmpeg ===
echo [3/3] Dong app roi thay ffmpeg...
taskkill /F /IM ViralCrawl.exe >nul 2>&1
taskkill /F /IM ffmpeg.exe >nul 2>&1
timeout /t 2 /nobreak >nul

copy /Y "!FOUND!\ffmpeg.exe"  "!FOUND!\ffmpeg.exe.8bak"  >nul 2>&1
copy /Y "!FOUND!\ffprobe.exe" "!FOUND!\ffprobe.exe.8bak" >nul 2>&1
copy /Y "!NEWBIN!\ffmpeg.exe"  "!FOUND!\ffmpeg.exe"  >nul 2>&1
copy /Y "!NEWBIN!\ffprobe.exe" "!FOUND!\ffprobe.exe" >nul 2>&1
if not exist "!FOUND!\ffmpeg.exe" (
  echo [X] Khong ghi duoc ^(can chay CMD bang quyen Administrator vi app o Program Files^).
  echo     Chuot phai vao file nay -^> "Run as administrator".
  goto :END
)

echo.
echo --- ffmpeg sau khi thay ---
"!FOUND!\ffmpeg.exe" -version 2>nul | findstr /B "ffmpeg version"
echo.

echo --- Test NVENC (GPU) ---
"!FOUND!\ffmpeg.exe" -hide_banner -loglevel error -f lavfi -i "color=c=black:s=256x256:d=0.3" -c:v h264_nvenc -preset p4 -rc vbr -cq 28 -b:v 0 -f null - 2>nul
if !errorlevel!==0 (
  echo [OK] NVENC CHAY DUOC ! Mo lai app va render - se nhanh len nhieu.
) else (
  echo [!] NVENC van chua chay. Chup man hinh nay gui ho tro.
)

rmdir /s /q "%TMP7%" 2>nul
echo.
echo ==================================================
echo   XONG. Mo lai app ViralCrawl va render lai.
echo ==================================================
:END
pause
