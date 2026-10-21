@echo off
chcp 65001 >nul
cd /d "%~dp0"
:: --- Chon PYTHON dung (them 06/08/2026) ---------------------------------------------------
:: Ban DEV (chay tu repo) co Meowcrawler\.venv. Ban DA CAI cho khach (resources\app-src) KHONG
:: co thu muc do -> truoc day tro cung vao day nen bam file .bat nay la CHET NGAY.
:: Nay lui ve runtime venv o userData - dung cho ma CHAY-WEB.bat va desktop\main.js dang dung.
set "VCPYW=%~dp0Meowcrawler\.venv\Scripts\pythonw.exe"
if not exist "%VCPYW%" set "VCPYW=%APPDATA%\viralcrawl-desktop\runtime\venv\Scripts\pythonw.exe"
set "VCPY=%~dp0Meowcrawler\.venv\Scripts\python.exe"
if not exist "%VCPY%" set "VCPY=%APPDATA%\viralcrawl-desktop\runtime\venv\Scripts\python.exe"
:: ---------------------------------------------------------------------------------------------
:: Khoi dong server web (neu chua chay) roi mo localhost trong Chrome che do app - 1 lan bam la xong
set "URL=http://localhost:8770"

:: 1) Bat server neu chua chay
:: BUG FIX: badge đọc profile cũ ở repo → báo "out" oan. Phải set MC_BROWSER_DATA_DIR đến AppData/viralcrawl-desktop/browser_data (nơi login lưu cookie).
set "MC_BROWSER_DATA_DIR=%AppData%\viralcrawl-desktop\browser_data"
powershell -NoProfile -Command "if(-not (Get-NetTCPConnection -LocalPort 8770 -State Listen -ErrorAction SilentlyContinue)){ Start-Process -WindowStyle Hidden -FilePath '%VCPYW%' -ArgumentList 'web_app.py','--noopen' -WorkingDirectory '%~dp0'; Start-Sleep -Seconds 2 }"

:: 2) Tim trinh duyet Chromium (Chrome truoc, roi Edge)
set "BROWSER="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "BROWSER=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "BROWSER=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "BROWSER=%LocalAppData%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "BROWSER=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not defined BROWSER if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "BROWSER=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"

:: 3) Mo localhost
if not defined BROWSER goto mac_dinh
start "" "%BROWSER%" --app=%URL% --window-size=1400,900
goto xong

:mac_dinh
:: Khong tim thay Chrome/Edge -> mo bang trinh duyet mac dinh
start "" %URL%

:xong
exit
