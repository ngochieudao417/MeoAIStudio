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
if not exist "%VCPYW%" (
    echo Chua cai moi truong! Dang tu dong chay cai dat...
    call CAI-DAT.bat
)
echo Dang khoi dong server web...
:: Bat server neu chua chay, roi DOI den khi san sang moi mo trinh duyet (tranh "tu choi ket noi")
powershell -NoProfile -Command "if(-not (Get-NetTCPConnection -LocalPort 8770 -State Listen -ErrorAction SilentlyContinue)){ Start-Process -WindowStyle Hidden -FilePath '%VCPYW%' -ArgumentList 'web_app.py','--noopen' -WorkingDirectory '%~dp0' }; for($i=0;$i -lt 60;$i++){ if(Get-NetTCPConnection -LocalPort 8770 -State Listen -ErrorAction SilentlyContinue){break}; Start-Sleep -Milliseconds 250 }"
start "" http://localhost:8770
echo Giao dien web: http://localhost:8770  (dong cua so nay cung duoc)
