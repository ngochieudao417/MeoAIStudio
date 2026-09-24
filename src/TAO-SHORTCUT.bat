@echo off
chcp 65001 >nul
cd /d "%~dp0"
:: Tao shortcut "ViralCrawl" (icon.ico) tren Desktop + Start Menu -> lan sau chi bam icon la mo tool.
:: Shortcut tro toi MO-WEB.bat: bat server 8770 neu chua chay roi mo Chrome che do app.
:: Chay lai file nay bat cu luc nao de tao lai (vd sau khi cai lai Windows / doi thu muc du an).
:: GIU FILE NAY THUAN ASCII + xuong dong CRLF - chuoi co dau / LF deu lam cmd.exe parse sai.

set "DICH=%~dp0MO-WEB.bat"
set "ICON=%~dp0icon.ico"

if not exist "%DICH%" (echo [LOI] Khong thay MO-WEB.bat & pause & exit /b 1)
if not exist "%ICON%" (echo [LOI] Khong thay icon.ico & pause & exit /b 1)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $d='%DICH%'; $i='%ICON%'; $w='%~dp0'; foreach($t in @($ws.SpecialFolders('Desktop'),(Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'))){ if(-not (Test-Path $t)){continue}; $p=Join-Path $t 'ViralCrawl.lnk'; $s=$ws.CreateShortcut($p); $s.TargetPath=$d; $s.WorkingDirectory=$w; $s.IconLocation=$i; $s.WindowStyle=7; $s.Description='Mo ViralCrawl (tool cao video + long tieng)'; $s.Save(); Write-Host ('  [OK] '+$p) }"

echo.
echo Xong. Bam icon "ViralCrawl" tren Desktop de mo tool.
pause
