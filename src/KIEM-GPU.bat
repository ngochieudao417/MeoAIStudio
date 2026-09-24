@echo off
chcp 65001 >nul
title Kiem tra GPU - ViralCrawl
echo Dang kiem tra GPU... (lan dau mat 30-60 giay vi phai dung engine OCR)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0KIEM-GPU.ps1"
echo.
pause
