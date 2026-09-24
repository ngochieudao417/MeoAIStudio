@echo off
chcp 65001 >nul
cd /d "%~dp0"
:: --- Chon PYTHON dung (them 06/08/2026) ---------------------------------------------------
:: Ban DEV (chay tu repo) co MediaCrawler\.venv. Ban DA CAI cho khach (resources\app-src) KHONG
:: co thu muc do -> truoc day tro cung vao day nen bam file .bat nay la CHET NGAY.
:: Nay lui ve runtime venv o userData - dung cho ma CHAY-WEB.bat va desktop\main.js dang dung.
set "VCPYW=%~dp0MediaCrawler\.venv\Scripts\pythonw.exe"
if not exist "%VCPYW%" set "VCPYW=%APPDATA%\viralcrawl-desktop\runtime\venv\Scripts\pythonw.exe"
set "VCPY=%~dp0MediaCrawler\.venv\Scripts\python.exe"
if not exist "%VCPY%" set "VCPY=%APPDATA%\viralcrawl-desktop\runtime\venv\Scripts\python.exe"
:: ---------------------------------------------------------------------------------------------
:: KIEM TIENG - video render ra co tieng khong, va mat o dau.
:: Keo tha 1 thu muc (hoac 1 file mp4) vao file nay de kiem dung cho do.
:: GIU FILE NAY THUAN ASCII + CRLF - chuoi co dau lam cmd.exe parse sai.
set "PY=%VCPY%"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0kiem_tieng.py" %*
echo.
pause
