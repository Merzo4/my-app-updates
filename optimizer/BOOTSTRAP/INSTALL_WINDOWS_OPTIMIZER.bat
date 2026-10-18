@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Merzo Windows Optimizer - Official Stable 0.1.55.1
rem Verified GitHub Release mwo-v0.1.55.1, NOT the untested R57 candidate.
echo ===================================================
echo  MERZO WINDOWS OPTIMIZER - STABLE 0.1.55.1
echo ===================================================
echo Install source: official Merzo4/my-app-updates GitHub Release
echo Expected SHA-256: bda73f442a1726082372e8c4272668e0151c9d882df1350f417fadcc022a1035
echo This batch never removes user settings or previous installations by itself.
echo.
where curl.exe >nul 2>nul
if errorlevel 1 (
  echo ERROR: curl.exe is required.
  pause
  exit /b 2
)
where powershell.exe >nul 2>nul
if errorlevel 1 (
  echo ERROR: Windows PowerShell is required for SHA-256 verification.
  pause
  exit /b 3
)
rem Refuse a downgrade if a newer version is installed in Program Files.
powershell.exe -NoLogo -NoProfile -NonInteractive -Command "try { $p=Join-Path $env:ProgramFiles 'Merzo Windows Optimizer\MerzoWindowsOptimizer.exe'; if(Test-Path -LiteralPath $p) { $raw=(Get-Item -LiteralPath $p).VersionInfo.FileVersion; if([version]$raw -gt [version]'0.1.55.1'){ Write-Host ('A NEWER version is installed: '+$raw+'. Refusing downgrade.'); exit 20 } }; exit 0 } catch { Write-Error $_; exit 21 }"
if errorlevel 1 (
  echo ERROR: Existing version check refused the installation or failed.
  pause
  exit /b 4
)
set "WORK=%TEMP%\MerzoWindowsOptimizer-Official-0.1.55.1"
set "MWO_SETUP_PATH=%WORK%\MerzoWindowsOptimizerSetup-win-x64.exe"
set "EXPECTED=bda73f442a1726082372e8c4272668e0151c9d882df1350f417fadcc022a1035"
set "URL=https://github.com/Merzo4/my-app-updates/releases/download/mwo-v0.1.55.1/MerzoWindowsOptimizerSetup-win-x64.exe"
if not exist "%WORK%" mkdir "%WORK%"
if not exist "%WORK%" (
  echo ERROR: Cannot create temporary folder.
  pause
  exit /b 5
)
echo Downloading official installer (about 46 MB) ...
curl.exe -fL --retry 3 --connect-timeout 20 --max-time 900 "%URL%" -o "%MWO_SETUP_PATH%"
if errorlevel 1 (
  echo ERROR: Installer download failed.
  pause
  exit /b 6
)
set "ACTUAL="
for /f "usebackq delims=" %%H in (`powershell.exe -NoLogo -NoProfile -NonInteractive -Command "(Get-FileHash -LiteralPath $env:MWO_SETUP_PATH -Algorithm SHA256).Hash.ToLowerInvariant()"`) do set "ACTUAL=%%H"
if /I not "%ACTUAL%"=="%EXPECTED%" (
  echo ERROR: SHA-256 mismatch. Installer will NOT start.
  echo Expected: %EXPECTED%
  echo Actual:   %ACTUAL%
  del /q "%MWO_SETUP_PATH%" >nul 2>nul
  pause
  exit /b 7
)
echo SHA-256 verified.
echo.
echo The official installer will now open. Approve UAC only if expected.
start "" /wait "%MWO_SETUP_PATH%"
set "INSTALL_EXIT=%ERRORLEVEL%"
if "%INSTALL_EXIT%"=="0" (
  echo Installation process exited successfully.
  echo Check the program in Start Menu or Program Files.
  pause
  exit /b 0
)
if "%INSTALL_EXIT%"=="3010" (
  echo Installer requested a Windows restart.
  pause
  exit /b 0
)
echo ERROR: Installer exit code %INSTALL_EXIT%.
pause
exit /b %INSTALL_EXIT%
