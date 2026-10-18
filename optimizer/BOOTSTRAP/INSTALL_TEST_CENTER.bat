@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Merzo Optimizer - Install Local Test Center 0.1.7
rem Official pinned source: Merzo4/my-app-updates, commit edc83fca9f0f89fc895a0a30c7f58f81af143779
rem Test Center is independent of the stable Optimizer and requires drive D:.
echo ===================================================
echo  MERZO OPTIMIZER - LOCAL TEST CENTER 0.1.7
echo ===================================================
echo Source: GitHub / pinned commit edc83fca9f0f89fc895a0a30c7f58f81af143779
echo Install location: D:\MerzoOptimizer-LocalLab
echo Existing installed production Optimizer is not replaced.
echo.
if not exist "D:\" (
  echo ERROR: D: drive is required for the current Test Center 0.1.7.
  echo No disk or partition will be created automatically.
  pause
  exit /b 2
)
where curl.exe >nul 2>nul
if errorlevel 1 (
  echo ERROR: curl.exe is required.
  pause
  exit /b 3
)
where powershell.exe >nul 2>nul
if errorlevel 1 (
  echo ERROR: Windows PowerShell is required.
  pause
  exit /b 4
)
set "BASE=https://raw.githubusercontent.com/Merzo4/my-app-updates/edc83fca9f0f89fc895a0a30c7f58f81af143779/tools/MerzoOptimizer.LocalLab"
set "STAGE=%TEMP%\MerzoOptimizer-TestCenter-0.1.7-Pinned"
if not exist "%STAGE%" mkdir "%STAGE%"
if not exist "%STAGE%" (
  echo ERROR: Cannot create temporary bootstrap directory.
  pause
  exit /b 5
)
for %%F in (Bootstrap-PowerShell7.ps1 Start-TestCenter.ps1 MerzoOptimizer.LocalLab.ps1 Run-Profile.ps1 Run-Profile.Core.ps1 AUTO-REPORT.ps1 local-lab-profile.json ENABLE-DESTRUCTIVE-LAB.ps1 PACK-EVIDENCE.ps1 PUBLISH-EVIDENCE.ps1 Install-LocalLab.ps1 README.md) do (
  echo Downloading pinned file %%F...
  curl.exe -fL --retry 3 --connect-timeout 15 --max-time 120 "%BASE%/%%F" -o "%STAGE%\%%F"
  if errorlevel 1 (
    echo ERROR: Download failed: %%F. Nothing was installed by this batch.
    pause
    exit /b 6
  )
)
echo.
echo Bootstrap may install official PowerShell 7 and ask for UAC.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%STAGE%\Bootstrap-PowerShell7.ps1"
if errorlevel 1 (
  echo ERROR: PowerShell 7 bootstrap failed.
  pause
  exit /b 7
)
set "PWSH=C:\Program Files\PowerShell\7\pwsh.exe"
if not exist "%PWSH%" (
  echo ERROR: PowerShell 7 not present at expected path.
  pause
  exit /b 8
)
echo.
echo Installing/updating Local Test Center in D: ...
"%PWSH%" -NoLogo -NoProfile -STA -ExecutionPolicy Bypass -File "%STAGE%\Install-LocalLab.ps1"
if errorlevel 1 (
  echo ERROR: Test Center installation failed.
  echo See D:\MerzoOptimizer-LocalLab\Logs\gui-smoke.log if present.
  pause
  exit /b 9
)
echo.
echo OK: Test Center installed. The GUI was launched.
echo Use Diagnostics, Update Source, QUICK, then FULL SAFE.
echo GAME to RESTORE is blocked on a normal workstation.
exit /b 0
