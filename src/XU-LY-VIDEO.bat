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
echo ============================================
echo  BO XU LY VIDEO (FFmpeg) - dang chay nen
echo  Quet thu muc raw_videos, xu ly -> processed_videos
echo  Nhan Ctrl+C de dung.
echo ============================================
"%VCPY%" xu_ly_video.py
pause
