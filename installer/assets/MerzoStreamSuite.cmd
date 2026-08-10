@echo off
setlocal
cd /d "%~dp0"
title MerzoStream Suite
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher\MerzoStreamLauncher.ps1" %*
if errorlevel 1 (
  echo.
  echo MerzoStream Suite launcher returned an error. See %%LOCALAPPDATA%%\MerzoStreamSuite\logs\launcher5.log
  pause
)
