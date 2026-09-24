@echo off
title MO TRINH DUYET DANG NHAP - LOCAL STUDIO
cd /d "%~dp0"
cls
echo ===================================================================
echo     VIRALCRAWL LOCAL STUDIO - MO TRINH DUYET DANG NHAP NEN TANG
echo ===================================================================
echo.
echo   [1] Douyin - TikTok Trung Quoc
echo   [2] Bilibili
echo   [3] Xiaohongshu - Tieu Hong Thu
echo   [4] YouTube - Dang nhap tai khoan Google
echo   [5] Kuaishou
echo   [6] Weibo
echo.
echo ===================================================================
set /p choice="Nhap so chon (1-6): "

if "%choice%"=="1" goto dy
if "%choice%"=="2" goto bili
if "%choice%"=="3" goto xhs
if "%choice%"=="4" goto yt
if "%choice%"=="5" goto ks
if "%choice%"=="6" goto wb
goto end

:dy
echo Dang mo trinh duyet Douyin...
.venv\Scripts\python.exe src\mo_dang_nhap.py dy
goto end

:bili
echo Dang mo trinh duyet Bilibili...
.venv\Scripts\python.exe src\mo_dang_nhap.py bili
goto end

:xhs
echo Dang mo trinh duyet Xiaohongshu...
.venv\Scripts\python.exe src\mo_dang_nhap.py xhs
goto end

:yt
echo Dang mo trinh duyet YouTube - Google Login...
.venv\Scripts\python.exe src\mo_dang_nhap.py yt
goto end

:ks
echo Dang mo trinh duyet Kuaishou...
.venv\Scripts\python.exe src\mo_dang_nhap.py ks
goto end

:wb
echo Dang mo trinh duyet Weibo...
.venv\Scripts\python.exe src\mo_dang_nhap.py wb
goto end

:end
echo.
echo Hoan tat.
