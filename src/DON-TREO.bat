@echo off
chcp 65001 >nul
title Don treo render - ViralCrawl
echo.
echo ========================================================
echo   DON TREO RENDER - ViralCrawl
echo ========================================================
echo   Dung khi render DUNG YEN o "Chuan bi nguon" / "Khop tieng"
echo   khong nhuc nhich (bug ban cu). Script nay:
echo     - Dung cac tien trinh render bi treo
echo     - Dong cua so Chrome dich (Gemini) bi ket
echo     - Xoa khoa (.lock) bi ro ri lam render cho mai
echo   KHONG dong app ViralCrawl (app van chay, render lai duoc).
echo ========================================================
echo.
pause

echo.
echo [1/4] Dung tien trinh render bi treo (render_worker / xu_ly_chon)...
rem Chi kill python dang chay render_worker.py hoac xu_ly_chon.py — KHONG kill web_app (app chinh)
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object { $_.CommandLine -match 'render_worker|xu_ly_chon' } | ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('  da dung PID ' + $_.ProcessId) } catch {} }"

echo.
echo [2/4] Dung ffmpeg treo (deadlock buoc 'Khop tieng goc')...
powershell -NoProfile -Command "Get-Process ffmpeg -ErrorAction SilentlyContinue | ForEach-Object { try { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue; Write-Host ('  da dung ffmpeg PID ' + $_.Id) } catch {} }"

echo.
echo [3/4] Dong Chrome dich (Gemini) bi ro ri...
rem CHI dong Chrome dung profile Gemini cua tool (vc_gemini_profile / gemini_user_data / gemini_prefetch)
rem — KHONG dong Chrome ban dang luot web binh thuong.
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object { $_.CommandLine -match 'vc_gemini_profile|gemini_user_data|gemini_prefetch' } | ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }; Write-Host '  da dong Chrome dich (neu co)'"

echo.
echo [4/4] Xoa khoa (.lock) bi ro ri...
rem Lock scan-cache o thu muc _cache_artifact (anh-em voi data, ben userData).
set "CACHE1=%APPDATA%\viralcrawl-desktop\_cache_artifact"
set "CACHE2=%LOCALAPPDATA%\viralcrawl-desktop\_cache_artifact"
if exist "%CACHE1%" (
  del /q "%CACHE1%\*.lock" 2>nul
  echo   da xoa khoa o %CACHE1%
)
if exist "%CACHE2%" (
  del /q "%CACHE2%\*.lock" 2>nul
  echo   da xoa khoa o %CACHE2%
)
rem Xoa luon SingletonLock cua profile Gemini (Chrome cu giu khoa -> Chrome moi mo loi)
for %%D in ("%APPDATA%\viralcrawl-desktop\MediaCrawler\browser_data" "%TEMP%\vc_gemini_profile_worker") do (
  if exist "%%~D" del /s /q "%%~D\*SingletonLock" 2>nul
)

echo.
echo ========================================================
echo   XONG! Da don treo.
echo   Bay gio quay lai app ViralCrawl, bam Render lai.
echo   (Neu app cung dang do, dong app roi mo lai bang MO-WEB.bat)
echo ========================================================
echo.
pause
