@echo off
setlocal
where pwsh.exe >nul 2>nul
if errorlevel 1 (
  echo PowerShell 7 ^(pwsh.exe^) ne nayden.
  echo Ustanovi PowerShell 7 i zapusti etot fail snova.
  pause
  exit /b 1
)
pwsh.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-LocalLab.ps1"
if errorlevel 1 pause
