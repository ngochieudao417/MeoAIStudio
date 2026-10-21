@echo off
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
:: ============================================================
:: AUTO-RENDER NEN DA TAT (theo yeu cau cua user).
:: Render BAY GIO chi chay khi bam nut "Tu dong" trong tab Render
:: cua web (dung hang doi rieng, KHONG dung file nay).
:: De BAT LAI auto-render nen: bo dau :: o dong duoi.
:: "%VCPYW%" xu_ly_video.py
:: ============================================================
exit /b 0
